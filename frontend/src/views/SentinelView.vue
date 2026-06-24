<script setup lang="ts">
  import { ref, computed, nextTick, onMounted, onUnmounted } from 'vue';
  import api from '@/services/api';

  // --- INTERFACES ---
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
          # On utilise la même référence d'image que celle qui vient d'être buildée
    label: string;
    sourceIp?: string;
    targetIp?: string;
  }

  /**
   * API Response structure for the Sentinel Map.
   */
  interface SentinelMapResponse {
    nodes: PodNode[];
    edges: NetworkEdge[];
    namespaces: string[];
  }

  // --- REACTIVE STATE ---
  const pods = ref<PodNode[]>([]);
  const edges = ref<NetworkEdge[]>([]);
  const selectedNS = ref('all-protected');
  const isLoading = ref(false);
  const namespaces = ref(['all-protected']);

  // --- UI STATES ---
  const showRoleModal = ref(false);
  const selectedPod = ref<PodNode | null>(null);
  const currentViewMode = ref('list');
  const activeAccordion = ref<string | null>(null);
  const isHardened = ref(false); // Track the deployment status

  // --- LOGIC: SECURITY ANALYSIS ---
  const isVulnerable = (pod: PodNode) => {
    if (!pod || !pod.role) return true; 
    return !pod.is_hardened;
  };

  /**
 * Fetches the current Sentinel status to update the UI buttons accordingly.
 */
  const fetchSentinelStatus = async () => {
  try {
    const response = await api.get('/sentinel/status');
    console.log("DEBUG: Réponse brute:", response);
    isHardened.value = response.data.deployed;
    console.log("DEBUG: isHardened mis à jour à:", isHardened.value);
  } catch (error) {
    console.error("DEBUG: Erreur API:", error);
  }
};

  /**
   * Computes the global security score based on hardened vs vulnerable pods.
   */
  const securityStats = computed(() => {
    if (pods.value.length === 0) return { score: 100, vulnerableCount: 0 };
    const vulnerable = pods.value.filter(p => isVulnerable(p)).length;
    const score = Math.round(((pods.value.length - vulnerable) / pods.value.length) * 100);
    return { score, vulnerableCount: vulnerable };
  });

  /**
   * Filters and sorts pods based on the selected namespace.
   * Vulnerable pods are prioritized in the list for visibility.
   */
  const filteredPods = computed(() => {
    const list = selectedNS.value === 'all-protected' 
      ? pods.value 
      : pods.value.filter(pod => pod.namespace === selectedNS.value);
    
    return [...list].sort((a, b) => (isVulnerable(b) ? 1 : 0) - (isVulnerable(a) ? 1 : 0));
  });

  /**
   * Groups filtered pods by their respective Kubernetes namespace.
   */
  const podsByNamespace = computed(() => {
    return filteredPods.value.reduce((acc, pod) => {
      if (!acc[pod.namespace]) acc[pod.namespace] = [];
      acc[pod.namespace]!.push(pod); 
      return acc;
    }, {} as Record<string, PodNode[]>);
  });

  /**
   * Filters network edges to only show connections relevant to the current namespace.
   */
  const filteredEdges = computed(() => {
    if (selectedNS.value === 'all-protected') return edges.value;
    const nsPodIds = filteredPods.value.map(p => p.id);
    return edges.value.filter(edge => nsPodIds.includes(edge.source) && nsPodIds.includes(edge.target));
  });

  // --- DATA FETCHING ---

  /**
   * Synchronizes the network map from the Sentinel backend service.
   */
  /**
   * Fetches the network topology for the Sentinel module.
   * Includes a safety watchdog timer to detect hung requests.
   */
  let abortController: AbortController | null = null;

  /**
   * Synchronizes the network topology from the Sentinel backend.
   * Implements robust error handling and concurrency control to ensure UI stability.
   */

  const fetchNetworkData = async () => {

    if (isLoading.value) return; 

    if (abortController) abortController.abort();
    abortController = new AbortController();
    isLoading.value = true;

    try {
      // API call with AbortSignal for request cancellation
      const response = await api.get<SentinelMapResponse>('/sentinel/map', {
        signal: abortController.signal
      });

      const { data } = response;

      // 3. Wait for DOM to be ready for incoming data
      await nextTick();

      // 4. Atomic state updates
      pods.value = data.nodes || [];
      namespaces.value = data.namespaces 
        ? ['all-protected', ...data.namespaces] 
        : ['all-protected'];

      // 5. Edge mapping with safe lookup for associated IPs
      edges.value = (data.edges || []).map(edge => ({
        ...edge,
        sourceIp: pods.value.find(p => p.id === edge.source)?.ip || '0.0.0.0',
        targetIp: pods.value.find(p => p.id === edge.target)?.ip || '0.0.0.0'
      }));

      console.info("DEBUG: Network topology data successfully applied to state");

    } catch (error: any) {
      // 6. Fine-grained error handling
      if (error.name === 'AbortError' || error.name === 'CanceledError') {
        console.warn("DEBUG: Request aborted due to navigation.");
        return; 
      }
      
      console.error("DEBUG: Critical synchronization error:", error);
      
      // Reset state to prevent UI inconsistency in case of API failure
      pods.value = [];
      edges.value = [];
      namespaces.value = ['all-protected'];
      isLoading.value = false;
      
    } finally {
      // 7. Final Cleanup: Ensure loading state is reset
      if (abortController && !abortController.signal.aborted) {
        isLoading.value = false;
      }
    }
  };
    

  // --- TOPOLOGY HELPERS ---
  const getNodePos = (_id: string, index: number, total: number, side: 'left' | 'right') => {
    const x = side === 'left' ? 150 : 850;
    const y = (index + 1) * (500 / (total + 1));
    return { x, y };
  };

  // --- TOPOLOGY HELPERS ---
  const getEdgePath = (edge: NetworkEdge) => {
    
    if (!pods.value || pods.value.length === 0) return "";
    
    const sourceIdx = filteredPods.value.findIndex(p => p.id === edge.source);
    const targetIdx = filteredPods.value.findIndex(p => p.id === edge.target);

    if (sourceIdx === -1 || targetIdx === -1) return "";

    const total = filteredPods.value.length;
    const start = getNodePos(edge.source, sourceIdx, total, sourceIdx % 2 === 0 ? 'left' : 'right');
    const end = getNodePos(edge.target, targetIdx, total, targetIdx % 2 === 0 ? 'left' : 'right');
    
    return `M ${start.x} ${start.y} C ${(start.x + end.x)/2} ${start.y}, ${(start.x + end.x)/2} ${end.y}, ${end.x} ${end.y}`;
  };

  // --- SENTINEL ACTIONS ---

  const triggerHarden = async () => {

  if (!confirm("🚨 Apply Network Sentinel hardening?")) return;

  await api.post('/sentinel/activate', {});
  await fetchSentinelStatus(); // Refresh status after action
  fetchNetworkData();
};

  const triggerDeactivate = async () => {

  if (!confirm("⚠️ Deactivate Zero-Trust policies?")) return;

  await api.post('/sentinel/deactivate', {});
  await fetchSentinelStatus(); // Refresh status after action
  fetchNetworkData();
};

  const toggleAccordion = (id: string) => {
    activeAccordion.value = activeAccordion.value === id ? null : id;
  };

  const openRoleDetails = (pod: PodNode) => {
    selectedPod.value = pod;
    showRoleModal.value = true;
  };
  
  const init = async () => {
    console.log("DEBUG: Chargement frais des données Sentinel...");
    await Promise.all([fetchNetworkData(), fetchSentinelStatus()]);
  };

  onMounted(async () => {
  console.log("DEBUG: SentinelView MONTE");
  
  await nextTick(); 
  init(); 
});

  onUnmounted(() => {
    console.log("DEBUG: SentinelView en cours de nettoyage...");
    if (abortController) {
      abortController.abort(); 
    }
    
    pods.value = [];
    edges.value = [];
    isLoading.value = false;
    console.log("DEBUG: État nettoyé, prêt pour navigation.");
  });
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
            <button @click="init" class="bg-slate-800 hover:bg-slate-700 border border-slate-600 text-slate-300 px-4 py-1.5 rounded-sm text-[9px] font-bold uppercase tracking-widest transition-all">
              Refresh Audit
            </button>
            <template v-if="isHardened">
            <div class="px-3 py-1 bg-green-500/10 border border-green-500 text-green-500 text-[8px] font-black uppercase tracking-widest rounded-sm">
              Policies Active
            </div>
            <button @click="triggerDeactivate" class="bg-red-500/10 hover:bg-red-500/20 border border-red-500 text-red-500 px-4 py-1.5 rounded-sm text-[9px] font-bold uppercase tracking-widest transition-all">
              Deactivate Policies
            </button>
          </template>
          
          <template v-else>
            <button @click="triggerHarden" class="bg-[#f05a28]/10 hover:bg-[#f05a28]/20 border border-[#f05a28] text-[#f05a28] px-4 py-1.5 rounded-sm text-[9px] font-bold uppercase tracking-widest transition-all">
              Deploy Net Policies
            </button>
          </template>
        </div>
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
        
        <svg v-show="pods.length > 0" viewBox="0 0 1000 500" class="w-full h-full max-w-4xl relative z-10">
          <g v-for="edge in filteredEdges" :key="'base-' + edge.source + edge.target">
            <path v-if="getEdgePath(edge)" :d="getEdgePath(edge)" fill="none" class="stroke-slate-800 stroke-[1]" />
          </g>
          
          <g v-for="edge in filteredEdges" :key="'flow-' + edge.source + edge.target">
            <path v-if="getEdgePath(edge)" :d="getEdgePath(edge)" fill="none" class="stroke-blue-500 stroke-[1.5] opacity-60 animate-dash-flow" stroke-dasharray="4 8" />
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

        <div v-if="pods.length === 0 && !isLoading" class="text-slate-500 text-xs">
          Aucune donnée topologique disponible.
        </div>
      </div>

      <div v-if="currentViewMode === 'list'" class="space-y-6">
        <div v-for="(nsPods, nsName) in podsByNamespace" :key="nsName" class="space-y-3">
          <div class="flex items-center gap-3">
            <h3 class="text-[10px] font-black text-slate-600 uppercase tracking-[0.2em]">{{ nsName }}</h3>
            <div class="h-[1px] flex-1 bg-slate-800/40"></div>
          </div>

          <div class="space-y-2">
            <div v-for="pod in nsPods" :key="pod.id" class="border border-slate-800/60 rounded-sm overflow-hidden">
              <div @click="toggleAccordion(pod.id)" class="bg-[#111217] p-3 flex justify-between items-center cursor-pointer hover:bg-[#15171e] transition-colors">
                <div class="flex items-center gap-3">
                  <div :class="isVulnerable(pod) ? 'bg-red-500 shadow-[0_0_8px_rgba(239,68,68,0.5)]' : 'bg-blue-500 shadow-[0_0_8px_rgba(59,130,246,0.5)]'" class="w-1.5 h-1.5 rounded-full"></div>
                  <span class="text-[10px] font-bold text-white uppercase">{{ pod.name }}</span>
                </div>
                <span class="text-slate-500 text-[10px]">{{ activeAccordion === pod.id ? '−' : '+' }}</span>
              </div>

              <div v-if="activeAccordion === pod.id" class="bg-[#0b0c10] p-4 border-t border-slate-800/40">
                <div class="grid grid-cols-2 gap-4 text-[9px]">
                  <div>
                    <p class="text-slate-500 uppercase font-bold mb-1">IP Address</p>
                    <p class="text-blue-400 font-mono">{{ pod.ip }}</p>
                  </div>
                  <div>
                    <p class="text-slate-500 uppercase font-bold mb-1">Status</p>
                    <p :class="pod.status === 'Running' ? 'text-green-500' : 'text-yellow-500'">{{ pod.status }}</p>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
  </template>

  <style scoped>
  @keyframes dash-flow {
    from { stroke-dashoffset: 24; }
    to { stroke-dashoffset: 0; }
  }
  .animate-dash-flow {
    animation: dash-flow 1.5s linear infinite;
  }
  .custom-scrollbar::-webkit-scrollbar { width: 4px; }
  .custom-scrollbar::-webkit-scrollbar-thumb { background: #1e293b; border-radius: 2px; }
  </style>