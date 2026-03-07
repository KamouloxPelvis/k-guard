<script setup lang="ts">
  import { ref, computed, onMounted, watch } from 'vue';
  import api from '@/services/api';

  // --- Interfaces ---
  interface PodNode {
    id: string;
    name: string;
    namespace: string;
    status: string;
    ip: string;
    role: string;
    labels: Record<string, string>;
    image?: string; 
  }

  interface NetworkEdge {
    source: string;
    target: string;
    label: string;
    sourceIp?: string;
    targetIp?: string;
  }

  // --- Reactive State ---
  const pods = ref<PodNode[]>([]);
  const edges = ref<NetworkEdge[]>([]);
  const selectedNS = ref('all-protected');
  const isLoading = ref(false);
  const namespaces = ['all-protected', 'k-guard', 'blog-prod', 'portfolio-prod'];

  // --- UI States ---
  const showRoleModal = ref(false);
  const selectedPod = ref<PodNode | null>(null);
  const currentViewMode = ref('list'); 

  // --- Computed Filtering Logic ---
  const filteredPods = computed(() => {
    if (selectedNS.value === 'all-protected') return pods.value;
    return pods.value.filter(pod => pod.namespace === selectedNS.value);
  });

  const filteredEdges = computed(() => {
    if (selectedNS.value === 'all-protected') return edges.value;
    const nsPodIds = filteredPods.value.map(p => p.id);
    return edges.value.filter(edge => nsPodIds.includes(edge.source) || nsPodIds.includes(edge.target));
  });

  /**
   * Fetches real-time network mapping data from the Sentinel engine.
   */
  const fetchNetworkData = async () => {
    isLoading.value = true;
    try {
      const { data } = await api.get('/sentinel/map');
      pods.value = data.nodes || [];
      const rawEdges = data.edges || [];
      
      // Enrich edges with IP addresses for visual mapping
      edges.value = rawEdges.map((edge: NetworkEdge) => ({
        ...edge,
        sourceIp: pods.value.find(p => p.id === edge.source)?.ip || '?.?.?.?',
        targetIp: pods.value.find(p => p.id === edge.target)?.ip || '?.?.?.?'
      }));
    } catch (error) {
      pods.value = [];
      edges.value = [];
      console.error("Sentinel UI Sync Error", error);
    } finally {
      isLoading.value = false;
    }
  };

  const openRoleDetails = (pod: PodNode) => {
    selectedPod.value = pod;
    showRoleModal.value = true;
  };

  /**
   * Simple heuristic to flag potentially vulnerable workloads.
   */
  const isVulnerable = (pod: PodNode) => {
    return pod.image?.includes('nginx:1.18') || pod.labels?.app === 'blog-devopsnotes';
  };

  const runQuickAudit = async () => {
    await fetchNetworkData();
  };

  /**
   * Triggers the Ansible-based hardening process for the network layer.
   */
  const triggerHarden = async () => {
    if (!confirm("🚨 Apply Network Sentinel hardening to the cluster?")) return;
    try {
      await api.post('/sentinel/harden');
      alert("🛡️ Network Sentinel strategy applied successfully!");
    } catch (e) {
      alert("❌ Error: Ansible Playbook execution failed.");
    }
  };

  onMounted(fetchNetworkData);
  watch(selectedNS, fetchNetworkData);

  const getStatusColor = (status: string) => {
    if (status === 'Running' || status === 'Succeeded') return 'text-green-500 bg-green-500/10 border-green-500/20';
    return 'text-red-500 bg-red-500/10 border-red-500/20';
  };

  // --- Topology Mapping Data ---
  const uniqueSources = computed(() => [...new Set(filteredEdges.value.map(e => e.source))]);
  const uniqueTargets = computed(() => [...new Set(filteredEdges.value.map(e => e.target))]);
</script>

<template>
  <div class="p-6 lg:p-10 space-y-8 relative">
    
    <div class="flex flex-col md:flex-row md:items-center justify-between gap-6 bg-[#111217] p-6 border border-slate-800/60 rounded-sm">
      <div><p class="text-[12px] text-slate-500 uppercase tracking-[0.5em] leading-none">Micro-segmentation & Traffic Mapping</p></div>
      
      <div class="flex flex-wrap items-center gap-4">
        <div class="inline-flex p-1 bg-[#0b0c10] border border-slate-700 rounded-sm mr-4">
          <button @click="currentViewMode = 'list'" 
                  :class="currentViewMode === 'list' ? 'bg-blue-600 text-white' : 'text-slate-500 hover:text-slate-300'"
                  class="px-4 py-1 text-[9px] font-black uppercase tracking-widest transition-all rounded-sm cursor-pointer">List</button>
          <button @click="currentViewMode = 'topology'" 
                  :class="currentViewMode === 'topology' ? 'bg-orange-600 text-white' : 'text-slate-500 hover:text-slate-300'"
                  class="px-4 py-1 text-[9px] font-black uppercase tracking-widest transition-all rounded-sm cursor-pointer">Topology</button>
        </div>

        <select v-model="selectedNS" class="bg-[#0b0c10] border border-slate-700 text-[10px] text-slate-300 px-4 py-2 rounded-sm focus:border-[#f05a28] uppercase font-bold tracking-widest cursor-pointer">
          <option v-for="ns in namespaces" :key="ns" :value="ns">{{ ns }}</option>
        </select>
        <button @click="runQuickAudit" class="bg-blue-500/10 hover:bg-blue-500/20 border border-blue-500 text-blue-500 px-6 py-2 rounded-sm text-[10px] font-bold uppercase tracking-widest cursor-pointer">🔍 Quick Audit</button>
        <button @click="triggerHarden" class="bg-[#f05a28]/10 hover:bg-[#f05a28]/20 border border-[#f05a28] text-[#f05a28] px-6 py-2 rounded-sm text-[10px] font-bold uppercase tracking-widest cursor-pointer">Deploy Hardening</button>
      </div>
    </div>

    <div v-if="edges.length > 0 && !isLoading && currentViewMode === 'list'" class="bg-[#111217] border border-slate-800/60 p-8 rounded-sm shadow-2xl">
      <h3 class="text-xs font-bold text-slate-400 mb-10 uppercase tracking-widest flex items-center gap-3">
        <span class="w-3 h-3 bg-blue-500 rounded-full animate-pulse shadow-[0_0_10px_rgba(59,130,246,0.5)]"></span>
        Real-Time Traffic Architecture
      </h3>
      
      <div class="flex flex-col gap-12 py-6">
        <div v-for="edge in edges" :key="edge.source + edge.target" class="flex items-center justify-between gap-8 max-w-5xl mx-auto w-full group">
          <div class="flex-1 text-right">
            <div class="inline-block px-6 py-4 bg-blue-900/10 border border-blue-500/40 rounded-sm">
              <p class="text-[11px] text-white font-mono font-bold uppercase tracking-widest">{{ edge.source }}</p>
              <p class="text-[9px] text-blue-400/60 font-mono mt-2 tracking-tighter">{{ edge.sourceIp }}</p>
            </div>
          </div>
          <div class="flex flex-col items-center min-w-[250px] relative">
            <span class="text-[9px] text-[#f05a28] font-black animate-pulse mb-3 uppercase tracking-[0.2em]">
              {{ edge.label }} <span class="text-slate-600 ml-1 font-mono opacity-60">(TCP/443)</span>
            </span>
            <div class="h-[2px] w-full bg-slate-800 relative overflow-hidden rounded-full">
              <div class="absolute inset-0 bg-gradient-to-r from-blue-500 to-[#f05a28] opacity-80"></div>
              <div class="absolute top-0 bottom-0 w-20 bg-white/20 blur-sm animate-flow-particle"></div>
            </div>
          </div>
          <div class="flex-1 text-left">
            <div class="inline-block px-6 py-4 bg-[#f05a28]/5 border border-[#f05a28]/40 rounded-sm">
              <p class="text-[11px] text-white font-mono font-bold uppercase tracking-widest">{{ edge.target }}</p>
              <p class="text-[9px] text-orange-400/60 font-mono mt-2 tracking-tighter">{{ edge.targetIp }}</p>
            </div>
          </div>
        </div>
      </div>
    </div>

    <div v-if="edges.length > 0 && !isLoading && currentViewMode === 'topology'" class="bg-[#0b0c10] border border-slate-800/60 p-10 rounded-sm relative overflow-hidden min-h-[500px] flex items-center justify-center">
      <div class="absolute inset-0 opacity-10" style="background-image: radial-gradient(#3b82f6 1px, transparent 1px); background-size: 30px 30px;"></div>
      <div class="relative w-full max-w-6xl">
        <div class="grid grid-cols-3 gap-y-20 items-center">
          <div class="flex flex-col gap-12 items-end">
            <div v-for="source in uniqueSources" :key="source" class="topology-node source-node group relative flex items-center">
              <div class="node-box px-4 py-3 border border-blue-500/30 bg-blue-900/10 rounded-sm">
                <span class="text-[9px] text-white font-bold uppercase tracking-widest">{{ source }}</span>
              </div>
            </div>
          </div>
          <div class="flex flex-col items-center z-20">
            <div class="w-24 h-24 rounded-full border-2 border-orange-500/50 flex items-center justify-center bg-[#0b0c10] shadow-[0_0_30px_rgba(240,90,40,0.2)]">
               <div class="w-20 h-20 rounded-full bg-orange-500/10 flex items-center justify-center animate-pulse border border-orange-500/20">
                 <span class="text-[10px] text-orange-500 font-black text-center uppercase tracking-tighter">Network<br/>Sentinel</span>
               </div>
            </div>
          </div>
          <div class="flex flex-col gap-12 items-start">
            <div v-for="target in uniqueTargets" :key="target" class="topology-node target-node group relative flex items-center">
              <div class="node-box px-4 py-3 border border-orange-500/30 bg-orange-500/10 rounded-sm">
                <span class="text-[9px] text-white font-bold uppercase tracking-widest">{{ target }}</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <div v-if="!isLoading && currentViewMode === 'list'" class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
      <div v-for="pod in filteredPods" :key="pod.id" @click="openRoleDetails(pod)"
          :class="['bg-[#0d0e12] border p-5 rounded-sm hover:border-blue-500/40 transition-all group relative overflow-hidden cursor-pointer', isVulnerable(pod) ? 'border-red-600/50 animate-vulnerable' : 'border-slate-800/60']">
        <div class="flex items-start justify-between mb-4">
          <div class="flex flex-col">
            <span class="text-[9px] font-mono text-blue-400 leading-none mb-1">{{ pod.ip || '0.0.0.0' }}</span>
            <div class="p-2 bg-blue-600/10 rounded-sm w-fit">
              <span class="text-xl">{{ isVulnerable(pod) ? '⚠️' : '📦' }}</span>
            </div>
          </div>
          <span :class="['px-2 py-1 text-[8px] font-bold uppercase border rounded-full', getStatusColor(pod.status)]">
            {{ pod.status }}
          </span>
        </div>
        <h3 class="text-sm font-bold text-white truncate mb-1 uppercase tracking-tight">{{ pod.name }}</h3>
        <p class="text-[10px] text-slate-500 font-mono mb-4 uppercase tracking-widest">Namespace: {{ pod.namespace }}</p>
      </div>
    </div>

    <Teleport to="body">
      <div v-if="showRoleModal" class="fixed inset-0 z-[100] flex items-center justify-center p-6 bg-black/95 backdrop-blur-md">
        <div class="bg-[#0d0e12] border border-slate-800 w-full max-w-2xl h-[60vh] flex flex-col rounded-sm">
          
          <div class="p-4 border-b border-slate-800 flex justify-between items-center bg-[#181b1f]">
            <span class="text-[10px] font-mono text-orange-400 uppercase tracking-widest">
              RBAC Explorer // {{ selectedPod?.name }}
            </span>
            <button @click="showRoleModal = false" class="text-slate-500 hover:text-white text-2xl cursor-pointer transition-colors">&times;</button>
          </div>

          <div class="flex-1 p-6 overflow-y-auto font-mono text-[11px] bg-black/40 custom-scrollbar">
            
            <div class="mb-6 p-4 bg-blue-500/5 border-l-2 border-blue-500 rounded-r-sm">
              <p class="text-[9px] text-slate-500 uppercase font-bold mb-1">Detected Security Role</p>
              <p class="text-sm text-white font-black uppercase tracking-widest">{{ selectedPod?.role }}</p>
            </div>

            <div class="space-y-1">
              <p class="text-[9px] text-slate-500 uppercase font-bold mb-3 tracking-[0.2em]">Metadata & Labels</p>
              
              <div v-for="(val, key) in selectedPod?.labels" :key="key" 
                   class="flex items-center gap-4 py-2 border-b border-slate-900 group hover:bg-white/5 px-2 transition-colors">
                <span class="text-slate-500 min-w-[140px] uppercase font-bold text-[10px]">{{ key }}</span>
                <span class="text-blue-300 truncate">{{ val }}</span>
              </div>

              <div v-if="!selectedPod?.labels || Object.keys(selectedPod.labels).length === 0" class="text-slate-600 italic py-4">
                No metadata labels found for this workload.
              </div>
            </div>

            <div v-if="isVulnerable(selectedPod!)" 
                 class="mt-8 p-4 bg-red-900/10 border border-red-900/30 text-red-500 text-[10px] uppercase font-bold animate-pulse flex items-center gap-3">
              <span class="text-lg">⚠️</span>
              <div>
                <p>[ SECURITY ALERT ]</p>
                <p class="font-normal opacity-80 mt-1 uppercase">Potential vulnerability detected. Review active NetworkPolicies for this namespace.</p>
              </div>
            </div>
          </div>

          <div class="p-4 border-t border-slate-800 bg-[#0b0c10] flex justify-end">
             <button @click="showRoleModal = false" 
                     class="px-6 py-2 border border-slate-700 text-slate-400 text-[10px] font-bold uppercase tracking-widest hover:bg-slate-800 transition-all rounded-sm">
               Close Explorer
             </button>
          </div>

        </div>
      </div>
    </Teleport>
  </div>
</template>

<style scoped>
@keyframes flow-particle { 0% { left: -20%; opacity: 0; } 20% { opacity: 1; } 80% { opacity: 1; } 100% { left: 100%; opacity: 0; } }
.animate-flow-particle { animation: flow-particle 2s linear infinite; }
.animate-vulnerable { animation: border-pulse 2s infinite; }
@keyframes border-pulse { 0%, 100% { border-color: rgba(220, 38, 38, 0.4); } 50% { border-color: rgba(220, 38, 38, 0.9); } }
.custom-scrollbar::-webkit-scrollbar { width: 4px; }
.custom-scrollbar::-webkit-scrollbar-thumb { background: #1e293b; border-radius: 10px; }
</style>