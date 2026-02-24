<script setup lang="ts">
  import { ref, computed, onMounted, watch } from 'vue';
  import api from '@/services/api';

  interface PodNode {
    id: string;
    name: string;
    namespace: string;
    status: string;
    ip: string;
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

  const pods = ref<PodNode[]>([]);
  const edges = ref<NetworkEdge[]>([]);
  const selectedNS = ref('all-protected');
  const isLoading = ref(false);
  const namespaces = ['all-protected', 'k-guard', 'blog-prod', 'portfolio-prod'];

  // --- ETATS POUR LA MODALE DE ROLES ---
  const showRoleModal = ref(false);
  const selectedPod = ref<PodNode | null>(null);
  
  // --- GESTION DES VUES ---
  const currentViewMode = ref('list'); // 'list' ou 'topology'

  const fetchNetworkData = async () => {
    isLoading.value = true;
    try {
      const { data } = await api.get('/sentinel/map');
      pods.value = data.nodes || [];
      edges.value = data.edges || [];
      
      // Enrichissement des flux avec les IPs pour la partie graphique
      edges.value = edges.value.map(edge => ({
        ...edge,
        sourceIp: pods.value.find(p => p.id === edge.source)?.ip || '?.?.?.?',
        targetIp: pods.value.find(p => p.id === edge.target)?.ip || '?.?.?.?'
      }));
    } catch (error) {
      pods.value = [];
      edges.value = [];
      console.error("Sentinel UI Error", error);
    } finally {
      isLoading.value = false;
    }
  };

  const openRoleDetails = (pod: PodNode) => {
    selectedPod.value = pod;
    showRoleModal.value = true;
  };

  const isVulnerable = (pod: PodNode) => {
    return pod.image?.includes('nginx:1.18') || pod.labels?.app === 'blog-devopsnotes';
  };

  const runQuickAudit = async () => {
    await fetchNetworkData();
  };

  const triggerHarden = async () => {
    if (!confirm("🚨 Apply Network Sentinel hardening to the cluster?")) return;
    try {
      await api.post('/sentinel/harden');
      alert("🛡️ Stratégie Network Sentinel appliquée avec succès !");
    } catch (e) {
      alert("❌ Erreur lors de l'application du Playbook Ansible.");
    }
  };

  onMounted(fetchNetworkData);
  watch(selectedNS, fetchNetworkData);

  const getStatusColor = (status: string) => {
    if (status === 'Running' || status === 'Succeeded') return 'text-green-500 bg-green-500/10 border-green-500/20';
    return 'text-red-500 bg-red-500/10 border-red-500/20';
  };

  // --- DONNEES POUR LA TOPOLOGIE ---
  const uniqueSources = computed(() => {
    return [...new Set(edges.value.map(e => e.source))];
  });

  const uniqueTargets = computed(() => {
    return [...new Set(edges.value.map(e => e.target))];
  });
</script>

<template>
  <div class="p-6 lg:p-10 space-y-8 relative">
    
    <div class="flex flex-col md:flex-row md:items-center justify-between gap-6 bg-[#111217] p-6 border border-slate-800/60 rounded-sm">
      <div>
        <p class="text-[12px] text-slate-500 uppercase tracking-[0.5em] leading-none">
          IDS & Traffic Mapping
        </p>
      </div>
      
      <div class="flex flex-wrap items-center gap-4">
        <div class="inline-flex p-1 bg-[#0b0c10] border border-slate-700 rounded-sm mr-4">
          <button @click="currentViewMode = 'list'" 
                  :class="currentViewMode === 'list' ? 'bg-blue-600 text-white' : 'text-slate-500 hover:text-slate-300'"
                  class="px-4 py-1 text-[9px] font-black uppercase tracking-widest transition-all rounded-sm cursor-pointer">
            List
          </button>
          <button @click="currentViewMode = 'topology'" 
                  :class="currentViewMode === 'topology' ? 'bg-orange-600 text-white' : 'text-slate-500 hover:text-slate-300'"
                  class="px-4 py-1 text-[9px] font-black uppercase tracking-widest transition-all rounded-sm cursor-pointer">
            Topology
          </button>
        </div>

        <select v-model="selectedNS" 
                class="bg-[#0b0c10] border border-slate-700 text-[10px] text-slate-300 px-4 py-2 rounded-sm focus:outline-none focus:border-[#f05a28] uppercase font-bold tracking-widest cursor-pointer">
          <option v-for="ns in namespaces" :key="ns" :value="ns">{{ ns }}</option>
        </select>
        <button @click="runQuickAudit" class="bg-blue-500/10 hover:bg-blue-500/20 border border-blue-500 text-blue-500 px-6 py-2 rounded-sm text-[10px] font-bold uppercase tracking-widest transition-all cursor-pointer">
            🔍 Quick Audit
        </button>
        <button @click="triggerHarden" class="bg-[#f05a28]/10 hover:bg-[#f05a28]/20 border border-[#f05a28] text-[#f05a28] px-6 py-2 rounded-sm text-[10px] font-bold uppercase tracking-widest transition-all cursor-pointer">
          Deploy Hardening
        </button>
      </div>
    </div>

    <div v-if="edges.length > 0 && !isLoading && currentViewMode === 'list'" class="bg-[#111217] border border-slate-800/60 p-8 rounded-sm shadow-2xl">
      <h3 class="text-xs font-bold text-slate-400 mb-10 uppercase tracking-widest flex items-center gap-3">
        <span class="w-3 h-3 bg-blue-500 rounded-full animate-pulse shadow-[0_0_10px_rgba(59,130,246,0.5)]"></span>
        Real-Time Traffic Architecture
      </h3>
      
      <div class="flex flex-col gap-12 py-6">
        <div v-for="edge in edges" :key="edge.source + edge.target" 
            class="flex items-center justify-between gap-8 max-w-5xl mx-auto w-full group">
          
          <div class="flex-1 text-right">
            <div class="inline-block px-6 py-4 bg-blue-900/10 border border-blue-500/40 rounded-sm group-hover:bg-blue-900/20 transition-all duration-500 shadow-lg">
              <p class="text-[11px] text-white font-mono font-bold uppercase tracking-widest">{{ edge.source }}</p>
              <p class="text-[9px] text-blue-400/60 font-mono mt-2 tracking-tighter">{{ edge.sourceIp }}</p>
            </div>
          </div>
          
          <div class="flex flex-col items-center min-w-[250px] relative">
            <span class="text-[9px] text-[#f05a28] font-black animate-pulse mb-3 uppercase tracking-[0.2em] drop-shadow-md">
              {{ edge.label }} <span class="text-slate-600 ml-1 font-mono opacity-60">(TCP/443)</span>
            </span>
            
            <div class="h-[2px] w-full bg-slate-800 relative overflow-hidden rounded-full">
              <div class="absolute inset-0 bg-gradient-to-r from-blue-500 via-[#f05a28] to-[#f05a28] opacity-80"></div>
              <div class="absolute top-0 bottom-0 w-20 bg-white/20 blur-sm animate-flow-particle"></div>
            </div>
            <div class="absolute -right-1 top-[21px] border-t-[6px] border-l-[8px] border-t-transparent border-b-[6px] border-b-transparent border-l-[#f05a28]"></div>
          </div>
          
          <div class="flex-1 text-left">
            <div class="inline-block px-6 py-4 bg-[#f05a28]/5 border border-[#f05a28]/40 rounded-sm group-hover:bg-[#f05a28]/10 transition-all duration-500 shadow-lg">
              <p class="text-[11px] text-white font-mono font-bold uppercase tracking-widest">{{ edge.target }}</p>
              <p class="text-[9px] text-orange-400/60 font-mono mt-2 tracking-tighter">{{ edge.targetIp }}</p>
            </div>
          </div>
          
        </div>
      </div>
    </div>

    <div v-if="edges.length > 0 && !isLoading && currentViewMode === 'topology'" class="bg-[#0b0c10] border border-slate-800/60 p-10 rounded-sm relative overflow-hidden min-h-[500px] flex items-center justify-center">
      
      <div class="absolute inset-0 opacity-10" 
           style="background-image: radial-gradient(#3b82f6 1px, transparent 1px); background-size: 30px 30px;"></div>

      <div class="relative w-full max-w-6xl">
        <h3 class="absolute -top-6 left-0 text-[10px] font-black text-blue-500/50 uppercase tracking-[0.5em]">
          K-Guard Sentinel // Logical Topology Map
        </h3>

        <div class="grid grid-cols-3 gap-y-20 items-center">
          
          <div class="flex flex-col gap-12 items-end">
            <div v-for="source in uniqueSources" :key="source" class="topology-node source-node group">
              <div class="node-box border-blue-500/30 bg-blue-900/10">
                <span class="node-label">{{ source }}</span>
              </div>
              <div class="connection-line-right"></div>
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
            <div v-for="target in uniqueTargets" :key="target" class="topology-node target-node group">
              <div class="connection-line-left"></div>
              <div class="node-box border-orange-500/30 bg-orange-500/10">
                <span class="node-label">{{ target }}</span>
              </div>
            </div>
          </div>

        </div>
      </div>
    </div>


    <div v-if="!isLoading" class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
      <div v-for="pod in pods" :key="pod.id" 
          @click="openRoleDetails(pod)"
          :class="[
            'bg-[#0d0e12] border p-5 rounded-sm hover:border-blue-500/40 transition-all group relative overflow-hidden cursor-pointer',
            isVulnerable(pod) ? 'border-red-600/50 shadow-[0_0_15px_-5px_rgba(220,38,38,0.3)] animate-vulnerable' : 'border-slate-800/60'
          ]">
        
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
        
        <div class="space-y-3 border-t border-slate-800/40 pt-4 flex justify-between items-center">
          <div class="flex flex-col">
            <span class="text-[7px] text-slate-600 uppercase font-black">Detected Role</span>
            <span class="text-[9px] text-orange-500 font-bold uppercase">{{ pod.labels?.app || 'Generic' }}</span>
          </div>
          <button class="text-[8px] font-bold uppercase bg-slate-800 px-3 py-1 hover:bg-blue-600 transition-colors rounded-sm cursor-pointer">
            View Roles
          </button>
        </div>
      </div>
    </div>

    <Teleport to="body">
      <div v-if="showRoleModal" class="fixed inset-0 z-[100] flex items-center justify-center p-6 bg-black/95 backdrop-blur-md">
        <div class="bg-[#0d0e12] border border-slate-800 w-full max-w-2xl h-[60vh] flex flex-col rounded-sm">
          <div class="p-4 border-b border-slate-800 flex justify-between items-center bg-[#181b1f]">
            <span class="text-[10px] font-mono text-orange-400 uppercase tracking-widest">
              RBAC Explorer // {{ selectedPod?.name }}
            </span>
            <button @click="showRoleModal = false" class="text-slate-500 hover:text-white text-2xl cursor-pointer">&times;</button>
          </div>
          <div class="flex-1 p-6 overflow-y-auto font-mono text-[11px] bg-black/40 custom-scrollbar">
            <div v-for="(val, key) in selectedPod?.labels" :key="key" class="mb-2 flex gap-4 border-b border-slate-900 pb-1">
              <span class="text-slate-500 min-w-[120px] uppercase font-bold">{{ key }}</span>
              <span class="text-blue-300">{{ val }}</span>
            </div>
            <div v-if="isVulnerable(selectedPod!)" class="mt-8 p-4 bg-red-900/10 border border-red-900/30 text-red-500 text-[10px] uppercase font-bold animate-pulse">
              [ SECURITY ALERT ] : Vulnerable image detected. Hardening suggested.
            </div>
          </div>
          <div class="p-3 border-t border-slate-900 bg-black/40 flex justify-between items-center text-[8px] text-slate-600">
            <span class="uppercase font-bold tracking-[0.3em]">Sentinel Role Engine v2.0</span>
            <span class="font-mono">Audit Path: {{ selectedPod?.namespace }} / labels</span>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<style scoped>
/* Animations communes */
.animate-vulnerable {
  animation: border-pulse 2s infinite;
}

@keyframes border-pulse {
  0% { border-color: rgba(220, 38, 38, 0.4); box-shadow: 0 0 0px rgba(220, 38, 38, 0); }
  50% { border-color: rgba(220, 38, 38, 0.9); box-shadow: 0 0 15px rgba(220, 38, 38, 0.2); }
  100% { border-color: rgba(220, 38, 38, 0.4); box-shadow: 0 0 0px rgba(220, 38, 38, 0); }
}

.group:hover::after {
  content: "";
  position: absolute;
  top: 0; left: 0; right: 0; height: 1px;
  background: linear-gradient(90deg, transparent, #f05a28, transparent);
  animation: scan 2s linear infinite;
}

@keyframes scan {
  0% { transform: translateY(-100%); }
  100% { transform: translateY(400%); }
}

/* Animations List View */
@keyframes flow-particle {
  0% { left: -20%; opacity: 0; }
  20% { opacity: 1; }
  80% { opacity: 1; }
  100% { left: 100%; opacity: 0; }
}

.animate-flow-particle {
  animation: flow-particle 2s linear infinite;
}

.group:hover .px-6 {
  transform: scale(1.02);
  border-color: rgba(240, 90, 40, 0.6);
}

/* Styles Topology Map */
.topology-node {
  @apply relative flex items-center;
}

.node-box {
  @apply px-4 py-3 border rounded-sm transition-all duration-300 hover:scale-110 hover:shadow-2xl z-10;
}

.node-label {
  @apply text-[9px] text-white font-mono uppercase font-bold tracking-widest;
}

.connection-line-right {
  @apply h-px w-20 bg-gradient-to-r from-blue-500 to-orange-500 absolute -right-20 opacity-30 group-hover:opacity-100 transition-opacity;
}

.connection-line-left {
  @apply h-px w-20 bg-gradient-to-r from-orange-500 to-blue-500 absolute -left-20 opacity-30 group-hover:opacity-100 transition-opacity;
}

.topology-node::after {
  content: '';
  @apply absolute w-1 h-1 bg-white rounded-full opacity-0 pointer-events-none;
  animation: pulse-data 3s infinite linear;
}

.source-node::after {
  animation: pulse-data-right 3s infinite linear;
}

.target-node::after {
  animation: pulse-data-left 3s infinite linear;
}

@keyframes pulse-data-right {
  0% { right: -20px; opacity: 0; }
  50% { opacity: 1; }
  100% { right: -80px; opacity: 0; }
}

@keyframes pulse-data-left {
  0% { left: -20px; opacity: 0; }
  50% { opacity: 1; }
  100% { left: -80px; opacity: 0; }
}
</style>