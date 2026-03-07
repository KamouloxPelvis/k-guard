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
    is_hardened: boolean;
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
  const namespaces = ref(['all-protected']);

  // --- UI States ---
  const showRoleModal = ref(false);
  const selectedPod = ref<PodNode | null>(null);
  const currentViewMode = ref('list'); 

  // --- Logic: Vulnerability Detection & Scoring ---
  const isVulnerable = (pod: PodNode) => !pod.is_hardened;

  const securityStats = computed(() => {
    if (pods.value.length === 0) return { score: 100, vulnerableCount: 0 };
    const vulnerable = pods.value.filter(p => isVulnerable(p)).length;
    const score = Math.round(((pods.value.length - vulnerable) / pods.value.length) * 100);
    return { score, vulnerableCount: vulnerable };
  });

  // --- Computed: Grouped & Filtered Data ---
  const filteredPods = computed(() => {
    const list = selectedNS.value === 'all-protected' 
      ? pods.value 
      : pods.value.filter(pod => pod.namespace === selectedNS.value);
    
    // Sort: Vulnerable pods first
    return [...list].sort((a, b) => (isVulnerable(b) ? 1 : 0) - (isVulnerable(a) ? 1 : 0));
  });

  const podsByNamespace = computed(() => {
    return filteredPods.value.reduce((acc, pod) => {
      // 1. We ensure the key exists
      if (!acc[pod.namespace]) {
        acc[pod.namespace] = [];
      }
      // 2. We use the '!' operator to tell TS: "Trust me, it's defined"
      acc[pod.namespace]!.push(pod); 
      return acc;
    }, {} as Record<string, PodNode[]>);
  });

  const filteredEdges = computed(() => {
    if (selectedNS.value === 'all-protected') return edges.value;
    const nsPodIds = filteredPods.value.map(p => p.id);
    return edges.value.filter(edge => nsPodIds.includes(edge.source) && nsPodIds.includes(edge.target));
  });

  const fetchNetworkData = async () => {
    isLoading.value = true;
    try {
      const { data } = await api.get('/sentinel/map');
      pods.value = data.nodes || [];
      if (data.namespaces) namespaces.value = ['all-protected', ...data.namespaces];

      const rawEdges = data.edges || [];
      edges.value = rawEdges.map((edge: NetworkEdge) => ({
        ...edge,
        sourceIp: pods.value.find(p => p.id === edge.source)?.ip || '?.?.?.?',
        targetIp: pods.value.find(p => p.id === edge.target)?.ip || '?.?.?.?'
      }));
    } catch (error) {
      console.error("Sentinel UI Sync Error", error);
    } finally {
      isLoading.value = false;
    }
  };

  // --- Topology Rendering Logic ---
  const getNodePos = (_id: string, index: number, total: number, side: 'left' | 'right') => {
    const x = side === 'left' ? 150 : 850;
    const y = (index + 1) * (600 / (total + 1));
    return { x, y };
  };

  const getEdgePath = (edge: NetworkEdge) => {
    const sourceIdx = pods.value.findIndex(p => p.id === edge.source);
    const targetIdx = pods.value.findIndex(p => p.id === edge.target);
    const start = getNodePos(edge.source, sourceIdx, pods.value.length, 'left');
    const end = getNodePos(edge.target, targetIdx, pods.value.length, 'right');
    
    return `M ${start.x} ${start.y} C ${(start.x + end.x)/2} ${start.y}, ${(start.x + end.x)/2} ${end.y}, ${end.x} ${end.y}`;
  };

  const openRoleDetails = (pod: PodNode) => {
    selectedPod.value = pod;
    showRoleModal.value = true;
  };

  const triggerHarden = async () => {
    if (!confirm("🚨 Apply Network Sentinel hardening to the cluster?")) return;
    try {
      await api.post('/sentinel/harden');
      alert("🛡️ Network Sentinel strategy applied successfully!");
      fetchNetworkData();
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
</script>

<template>
  <div class="p-6 lg:p-10 space-y-8 relative max-w-[1600px] mx-auto">
    
    <div class="grid grid-cols-1 lg:grid-cols-4 gap-6">
      <div class="lg:col-span-3 flex flex-col md:flex-row md:items-center justify-between gap-6 bg-[#111217] p-8 border border-slate-800/60 rounded-sm">
        <div>
          <p class="text-[10px] text-slate-500 uppercase tracking-[0.5em] mb-2">Automated Micro-segmentation</p>
          <h2 class="text-xl font-black text-white uppercase tracking-tighter">Network Sentinel <span class="text-blue-500">v2.0</span></h2>
        </div>
        
        <div class="flex flex-wrap items-center gap-4">
          <div class="inline-flex p-1 bg-[#0b0c10] border border-slate-700 rounded-sm">
            <button @click="currentViewMode = 'list'" :class="currentViewMode === 'list' ? 'bg-blue-600 text-white' : 'text-slate-500'" class="px-4 py-1 text-[9px] font-black uppercase tracking-widest rounded-sm transition-all">List</button>
            <button @click="currentViewMode = 'topology'" :class="currentViewMode === 'topology' ? 'bg-orange-600 text-white' : 'text-slate-500'" class="px-4 py-1 text-[9px] font-black uppercase tracking-widest rounded-sm transition-all">Topology</button>
          </div>
          <select v-model="selectedNS" class="bg-[#0b0c10] border border-slate-700 text-[10px] text-slate-300 px-4 py-2 rounded-sm uppercase font-bold tracking-widest cursor-pointer">
            <option v-for="ns in namespaces" :key="ns" :value="ns">{{ ns }}</option>
          </select>
          <button @click="triggerHarden" class="bg-[#f05a28]/10 hover:bg-[#f05a28]/20 border border-[#f05a28] text-[#f05a28] px-6 py-2 rounded-sm text-[10px] font-bold uppercase tracking-widest transition-all">Deploy Hardening</button>
        </div>
      </div>

      <div class="bg-[#111217] border border-slate-800/60 p-6 rounded-sm flex flex-col items-center justify-center">
        <p class="text-[9px] text-slate-500 uppercase font-bold mb-2">Cluster Security Score</p>
        <div class="relative flex items-center justify-center">
          <svg class="w-20 h-20 transform -rotate-90">
            <circle cx="40" cy="40" r="35" stroke="currentColor" stroke-width="4" fill="transparent" class="text-slate-800" />
            <circle cx="40" cy="40" r="35" stroke="currentColor" stroke-width="4" fill="transparent" :stroke-dasharray="220" :stroke-dashoffset="220 - (220 * securityStats.score) / 100" :class="securityStats.score < 50 ? 'text-red-500' : 'text-blue-500'" />
          </svg>
          <span class="absolute text-xl font-black text-white">{{ securityStats.score }}%</span>
        </div>
      </div>
    </div>

    <div v-if="currentViewMode === 'topology'" class="bg-[#0b0c10] border border-slate-800/60 p-4 rounded-sm relative min-h-[650px] overflow-hidden flex items-center justify-center">
      <div class="absolute inset-0 opacity-10" style="background-image: radial-gradient(#3b82f6 1px, transparent 1px); background-size: 30px 30px;"></div>
      
      <svg viewBox="0 0 1000 600" class="w-full h-full max-w-5xl relative z-10">
        <defs>
          <marker id="arrow" viewBox="0 0 10 10" refX="10" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
            <path d="M 0 0 L 10 5 L 0 10 z" fill="#334155" />
          </marker>
        </defs>

        <g v-for="edge in filteredEdges" :key="edge.source + edge.target">
          <path :d="getEdgePath(edge)" fill="none" class="stroke-slate-800 stroke-[1.5]" marker-end="url(#arrow)" />
          <circle r="3" fill="#f05a28" class="animate-pulse">
            <animateMotion :path="getEdgePath(edge)" dur="3s" repeatCount="indefinite" />
          </circle>
        </g>

        <g v-for="(pod, idx) in pods" :key="pod.id" @click="openRoleDetails(pod)" class="cursor-pointer group">
          <rect :x="getNodePos(pod.id, idx, pods.length, idx % 2 === 0 ? 'left' : 'right').x - 60" 
                :y="getNodePos(pod.id, idx, pods.length, idx % 2 === 0 ? 'left' : 'right').y - 25" 
                width="120" height="50" rx="4" 
                :class="[isVulnerable(pod) ? 'fill-red-950 stroke-red-500' : 'fill-slate-900 stroke-blue-500', 'stroke-[1] transition-all group-hover:stroke-white']" />
          <text :x="getNodePos(pod.id, idx, pods.length, idx % 2 === 0 ? 'left' : 'right').x" 
                :y="getNodePos(pod.id, idx, pods.length, idx % 2 === 0 ? 'left' : 'right').y + 5" 
                text-anchor="middle" class="fill-white text-[9px] font-mono font-bold uppercase">{{ pod.role.length > 15 ? pod.role.substring(0,12)+'...' : pod.role }}</text>
        </g>
      </svg>
      <div class="absolute bottom-6 right-6 text-[9px] text-slate-600 uppercase font-mono tracking-widest">Active Discovery Flows: {{ filteredEdges.length }}</div>
    </div>

    <div v-if="currentViewMode === 'list'" class="space-y-12">
      <div v-for="(nsPods, ns) in podsByNamespace" :key="ns" class="space-y-8">
        
        <div class="flex items-center gap-4">
          <h3 class="text-xs font-black text-slate-500 uppercase tracking-[0.3em]">{{ ns }}</h3>
          <div class="h-[1px] flex-1 bg-slate-800/60"></div>
          <span class="text-[10px] text-slate-600 font-mono">{{ filteredEdges.length }} Active Flow(s)</span>
        </div>

        <div class="bg-[#111217]/50 border border-slate-800/40 p-6 rounded-sm space-y-4">
          <div v-for="(edge, index) in filteredEdges" :key="index" 
              class="flex flex-col md:flex-row items-center justify-between gap-4 p-4 border border-slate-800/20 hover:bg-white/[0.02] transition-all group">
            
            <div class="flex-1 w-full bg-[#0d0e12] border border-blue-500/20 p-4 rounded-sm relative transition-all group-hover:border-blue-500/50">
              <p class="text-[10px] font-black text-white mb-1 uppercase truncate tracking-tighter">{{ edge.source }}</p>
              <p class="text-[9px] font-mono text-blue-400 opacity-70">{{ edge.sourceIp }}</p>
            </div>

            <div class="flex flex-col items-center min-w-[220px] px-2">
              <p class="text-[8px] font-black text-slate-500 uppercase tracking-[0.2em] mb-2 text-center">
                Intra-NS Flow <span class="text-slate-600 font-normal">(TCP/443)</span>
              </p>
              <div class="w-full h-[1px] bg-gradient-to-r from-blue-500 via-orange-500 to-red-500 relative overflow-hidden">
                <div class="absolute inset-0 bg-white/40 animate-[flow_2s_linear_infinite]"></div>
              </div>
            </div>

            <div class="flex-1 w-full bg-[#0d0e12] border border-orange-900/20 p-4 rounded-sm relative transition-all group-hover:border-orange-500/50">
              <p class="text-[10px] font-black text-white mb-1 uppercase truncate tracking-tighter">{{ edge.target }}</p>
              <p class="text-[9px] font-mono text-orange-400 opacity-70">{{ edge.targetIp }}</p>
            </div>

          </div>
        </div>
      </div>
    </div>

    <Teleport to="body">
      <div v-if="showRoleModal" class="fixed inset-0 z-[100] flex items-center justify-center p-6 bg-black/95 backdrop-blur-md">
        <div class="bg-[#0d0e12] border border-slate-800 w-full max-w-2xl h-[70vh] flex flex-col rounded-sm shadow-2xl">
          <div class="p-4 border-b border-slate-800 flex justify-between items-center bg-[#181b1f]">
            <span class="text-[10px] font-mono text-orange-400 uppercase tracking-widest">RBAC Explorer // {{ selectedPod?.name }}</span>
            <button @click="showRoleModal = false" class="text-slate-500 hover:text-white text-2xl transition-colors">&times;</button>
          </div>
          <div class="flex-1 p-8 overflow-y-auto font-mono text-[11px] bg-black/40 custom-scrollbar">
            <div class="mb-8 p-4 bg-blue-500/5 border-l-2 border-blue-500 rounded-r-sm">
              <p class="text-[9px] text-slate-500 uppercase font-bold mb-1">Detected Security Role</p>
              <p class="text-base text-white font-black uppercase tracking-widest">{{ selectedPod?.role }}</p>
            </div>
            <div class="space-y-1">
              <p class="text-[9px] text-slate-500 uppercase font-bold mb-4 tracking-[0.2em]">Workload Metadata</p>
              <div v-for="(val, key) in selectedPod?.labels" :key="key" class="flex items-center gap-4 py-2 border-b border-slate-900 group hover:bg-white/5 px-2">
                <span class="text-slate-500 min-w-[150px] uppercase font-bold text-[10px]">{{ key }}</span>
                <span class="text-blue-300 truncate">{{ val }}</span>
              </div>
            </div>
            <div v-if="isVulnerable(selectedPod!)" class="mt-8 p-6 bg-red-900/10 border border-red-900/30 text-red-500 text-[10px] uppercase font-bold animate-pulse flex items-center gap-4">
              <span class="text-2xl">⚠️</span>
              <p>Critical: No NetworkPolicy detected for this workload. It is currently exposed to all traffic in the namespace.</p>
            </div>
          </div>
          <div class="p-4 border-t border-slate-800 bg-[#0b0c10] flex justify-end">
             <button @click="showRoleModal = false" class="px-8 py-3 border border-slate-700 text-slate-400 text-[10px] font-bold uppercase tracking-widest hover:bg-slate-800 transition-all rounded-sm">Close Explorer</button>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<style scoped>
@keyframes flow {
  0% { transform: translateX(-100%); width: 20%; opacity: 0; }
  50% { opacity: 1; }
  100% { transform: translateX(400%); width: 20%; opacity: 0; }
}
  @keyframes border-pulse { 0%, 100% { border-color: rgba(220, 38, 38, 0.4); } 50% { border-color: rgba(220, 38, 38, 0.9); } }

  @keyframes shimmer {
  0% { transform: translateX(-100%); }
  100% { transform: translateX(100%); }
  }
  .custom-scrollbar::-webkit-scrollbar { width: 4px; }
  .custom-scrollbar::-webkit-scrollbar-thumb { background: #1e293b; border-radius: 10px; }
  .animate-vulnerable { animation: border-pulse 2s infinite; }

::-webkit-scrollbar {
  width: 5px;
}
::-webkit-scrollbar-track {
  background: #0b0c10;
}
::-webkit-scrollbar-thumb {
  background: #1e293b;
  border-radius: 2px;
}

</style>