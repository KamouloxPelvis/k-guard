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
    
    // Technical Note: Prioritize vulnerable pods in the display order
    return [...list].sort((a, b) => (isVulnerable(b) ? 1 : 0) - (isVulnerable(a) ? 1 : 0));
  });

  const podsByNamespace = computed(() => {
    // Optimized grouping logic to avoid unused variable errors (TS6133)
    return filteredPods.value.reduce((acc, pod) => {
      if (!acc[pod.namespace]) {
        acc[pod.namespace] = [];
      }
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
  // 1. Locate the pod indices within the FILTERED list (currently rendered on screen)
  const sourceIdx = filteredPods.value.findIndex(p => p.id === edge.source);
  const targetIdx = filteredPods.value.findIndex(p => p.id === edge.target);

  // 2. Safety check: if either pod is not in the selected namespace, do not render the connection
  if (sourceIdx === -1 || targetIdx === -1) return "";

  const total = filteredPods.value.length;

  // 3. Calculate start and end positions using the same alignment logic as the template nodes
  const start = getNodePos(edge.source, sourceIdx, total, sourceIdx % 2 === 0 ? 'left' : 'right');
  const end = getNodePos(edge.target, targetIdx, total, targetIdx % 2 === 0 ? 'left' : 'right');
  
  // 4. Generate the SVG Cubic Bezier curve path
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

</script>

<template>
  <div class="p-4 lg:p-6 space-y-4 relative max-w-[1600px] mx-auto">
    
    <div class="grid grid-cols-1 lg:grid-cols-4 gap-4">
      <div class="lg:col-span-3 flex flex-col md:flex-row md:items-center justify-between gap-4 bg-[#111217] p-5 border border-slate-800/60 rounded-sm">
        <div>
          <p class="text-[9px] text-slate-500 uppercase tracking-[0.4em] mb-1">Automated Micro-segmentation</p>
          <h2 class="text-lg font-black text-white uppercase tracking-tighter">Network Sentinel <span class="text-blue-500">v2.0</span></h2>
        </div>
        
        <div class="flex flex-wrap items-center gap-3">
          <div class="inline-flex p-1 bg-[#0b0c10] border border-slate-700 rounded-sm">
            <button @click="currentViewMode = 'list'" :class="currentViewMode === 'list' ? 'bg-blue-600 text-white' : 'text-slate-500'" class="px-3 py-1 text-[8px] font-black uppercase tracking-widest rounded-sm transition-all">List</button>
            <button @click="currentViewMode = 'topology'" :class="currentViewMode === 'topology' ? 'bg-orange-600 text-white' : 'text-slate-500'" class="px-3 py-1 text-[8px] font-black uppercase tracking-widest rounded-sm transition-all">Topology</button>
          </div>
          <select v-model="selectedNS" class="bg-[#0b0c10] border border-slate-700 text-[9px] text-slate-300 px-3 py-1.5 rounded-sm uppercase font-bold tracking-widest cursor-pointer">
            <option v-for="ns in namespaces" :key="ns" :value="ns">{{ ns }}</option>
          </select>
          <button @click="triggerHarden" class="bg-[#f05a28]/10 hover:bg-[#f05a28]/20 border border-[#f05a28] text-[#f05a28] px-4 py-1.5 rounded-sm text-[9px] font-bold uppercase tracking-widest transition-all">Deploy Hardening</button>
        </div>
      </div>

      <div class="bg-[#111217] border border-slate-800/60 p-4 rounded-sm flex flex-col items-center justify-center">
        <p class="text-[8px] text-slate-500 uppercase font-bold mb-1">Security Score</p>
        <div class="relative flex items-center justify-center">
          <svg class="w-16 h-16 transform -rotate-90">
            <circle cx="32" cy="32" r="28" stroke="currentColor" stroke-width="3" fill="transparent" class="text-slate-800" />
            <circle cx="32" cy="32" r="28" stroke="currentColor" stroke-width="3" fill="transparent" :stroke-dasharray="175" :stroke-dashoffset="175 - (175 * securityStats.score) / 100" :class="securityStats.score < 50 ? 'text-red-500' : 'text-blue-500'" />
          </svg>
          <span class="absolute text-md font-black text-white">{{ securityStats.score }}%</span>
        </div>
      </div>
    </div>

    <div v-if="currentViewMode === 'topology'" class="bg-[#0b0c10] border border-slate-800/60 p-2 rounded-sm relative min-h-[500px] overflow-hidden flex items-center justify-center">
      <div class="absolute inset-0 opacity-5" style="background-image: radial-gradient(#3b82f6 1px, transparent 1px); background-size: 20px 20px;"></div>
      
      <svg viewBox="0 0 1000 500" class="w-full h-full max-w-4xl relative z-10">
        <g v-for="edge in filteredEdges" :key="edge.source + edge.target">
          <path v-if="getEdgePath(edge)" :d="getEdgePath(edge)" fill="none" class="stroke-slate-800 stroke-[1]" marker-end="url(#arrow)" />
        </g>

        <g v-for="(pod, idx) in filteredPods" :key="pod.id" @click="openRoleDetails(pod)" class="cursor-pointer group">
          <rect :x="getNodePos(pod.id, idx, filteredPods.length, idx % 2 === 0 ? 'left' : 'right').x - 50" 
                :y="getNodePos(pod.id, idx, filteredPods.length, idx % 2 === 0 ? 'left' : 'right').y - 20" 
                width="100" height="40" rx="2" 
                :class="[isVulnerable(pod) ? 'fill-red-950 stroke-red-500' : 'fill-slate-900 stroke-blue-500', 'stroke-[1] transition-all group-hover:stroke-white']" />
          <text :x="getNodePos(pod.id, idx, filteredPods.length, idx % 2 === 0 ? 'left' : 'right').x" 
                :y="getNodePos(pod.id, idx, filteredPods.length, idx % 2 === 0 ? 'left' : 'right').y + 4" 
                text-anchor="middle" class="fill-white text-[8px] font-mono font-bold uppercase">
            {{ pod.role.length > 12 ? pod.role.substring(0,10)+'...' : pod.role }}
          </text>
        </g>
      </svg>
      <div class="absolute bottom-3 right-4 text-[8px] text-slate-700 uppercase font-mono tracking-widest italic">Flows: {{ filteredEdges.length }}</div>
    </div>

    <div v-if="currentViewMode === 'list'" class="space-y-6">
      <div v-for="(nsPods, nsName) in podsByNamespace" :key="nsName" class="space-y-3">
        
        <div class="flex items-center gap-3">
          <h3 class="text-[10px] font-black text-slate-600 uppercase tracking-[0.2em]">{{ nsName }}</h3>
          <div class="h-[1px] flex-1 bg-slate-800/40"></div>
        </div>

        <div class="bg-[#111217]/50 border border-slate-800/30 p-4 rounded-sm space-y-2">
          <div v-for="(edge, index) in filteredEdges.filter(e => nsPods.some(p => p.id === e.source))" :key="index" 
              class="flex flex-col md:flex-row items-center justify-between gap-2 p-2 border border-slate-800/10 hover:bg-white/[0.01] transition-all group">
            
            <div class="flex-1 w-full bg-[#0d0e12] border border-blue-500/10 p-2 rounded-sm transition-all group-hover:border-blue-500/30">
              <p class="text-[9px] font-bold text-white uppercase truncate">{{ edge.source }}</p>
              <p class="text-[8px] font-mono text-blue-500/60">{{ edge.sourceIp }}</p>
            </div>

            <div class="flex flex-col items-center min-w-[150px] px-2">
              <p class="text-[7px] font-bold text-slate-600 uppercase tracking-tighter mb-1">TCP/443</p>
              <div class="w-full h-[1px] bg-slate-800 relative overflow-hidden">
                <div class="absolute inset-0 bg-gradient-to-r from-transparent via-blue-500 to-transparent animate-[flow_2s_linear_infinite]"></div>
              </div>
            </div>

            <div class="flex-1 w-full bg-[#0d0e12] border border-orange-900/10 p-2 rounded-sm transition-all group-hover:border-orange-500/30">
              <p class="text-[9px] font-bold text-white uppercase truncate">{{ edge.target }}</p>
              <p class="text-[8px] font-mono text-orange-500/60">{{ edge.targetIp }}</p>
            </div>
          </div>
        </div>
      </div>
    </div>
    
    <Teleport to="body">
      <div v-if="showRoleModal" class="fixed inset-0 z-[100] flex items-center justify-center p-4 bg-black/90 backdrop-blur-sm">
        <div class="bg-[#0d0e12] border border-slate-800 w-full max-w-5xl h-[80vh] flex flex-col rounded-sm shadow-2xl overflow-hidden">
          <div class="p-3 border-b border-slate-800 flex justify-between items-center bg-[#111217]">
            <span class="text-[10px] font-mono text-orange-400 uppercase tracking-widest">Metadata Explorer // {{ selectedPod?.name }}</span>
            <button @click="showRoleModal = false" class="text-slate-500 hover:text-white text-2xl transition-colors">&times;</button>
          </div>

          <div class="flex-1 p-5 md:p-8 overflow-y-auto font-mono bg-[#090a0d] custom-scrollbar">
            <div class="mb-6 p-4 bg-blue-500/5 border-l-2 border-blue-600">
              <p class="text-[9px] text-slate-500 uppercase font-black mb-1">Detected Role</p>
              <p class="text-xl text-white font-black uppercase tracking-tight">{{ selectedPod?.role }}</p>
            </div>

            <div class="space-y-1">
              <p class="text-[9px] text-slate-500 uppercase font-black mb-4 tracking-widest flex items-center gap-2">
                <span class="w-3 h-[1px] bg-slate-700"></span> Metadata
              </p>
              <div v-for="(val, key) in selectedPod?.labels" :key="key" 
                  class="flex flex-col md:flex-row md:items-center gap-2 py-2 border-b border-white/[0.02] px-2">
                <span class="text-blue-500/70 font-bold text-[9px] uppercase min-w-[200px]">{{ key }}</span>
                <span class="text-slate-400 text-[10px] break-all bg-slate-900/30 px-2 py-0.5 rounded border border-slate-800/40">{{ val }}</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<style scoped>
/* Animations identiques mais optimisées pour la fluidité */
@keyframes flow {
  0% { transform: translateX(-100%); }
  100% { transform: translateX(100%); }
}
.custom-scrollbar::-webkit-scrollbar { width: 3px; }
.custom-scrollbar::-webkit-scrollbar-thumb { background: #1e293b; }
</style>