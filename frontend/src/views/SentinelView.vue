<script setup lang="ts">
import { ref, onMounted, watch } from 'vue';
import api from '@/services/api';

interface PodNode {
  id: string;
  name: string;
  namespace: string;
  status: string;
  ip: string;
  labels: Record<string, string>;
}

interface NetworkEdge {
  source: string;
  target: string;
  label: string;
}

const pods = ref<PodNode[]>([]);
const edges = ref<NetworkEdge[]>([]);
const selectedNS = ref('all-protected');
const isLoading = ref(false);
const namespaces = ['all-protected', 'k-guard', 'blog-prod', 'portfolio-prod'];

const fetchNetworkData = async () => {
  isLoading.value = true;
  try {
    const nsParam = selectedNS.value === 'all-protected' ? '' : `?ns=${selectedNS.value}`;
    const { data } = await api.get(`/sentinel/map${nsParam}`);
    
    // On mappe les données reçues du backend
    pods.value = data.nodes || [];
    edges.value = data.edges || [];
    
  } catch (error) {
    console.error("Sentinel: Fetch Error", error);
  } finally {
    isLoading.value = false;
  }
};

const runQuickAudit = async () => {
  console.log("[Sentinel] Starting Quick Audit...");
  await fetchNetworkData();
};

const triggerHarden = async () => {
  if (!confirm("🚨 Appliquer le durcissement Network Sentinel sur le cluster ?")) return;
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
  if (status === 'Running') return 'text-green-500 bg-green-500/10 border-green-500/20';
  if (status === 'Pending') return 'text-yellow-500 bg-yellow-500/10 border-yellow-500/20';
  return 'text-red-500 bg-red-500/10 border-red-500/20';
};
</script>

<template>
  <div class="p-6 lg:p-10 space-y-8">
    
    <div class="flex flex-col md:flex-row md:items-center justify-between gap-6 bg-[#111217] p-6 border border-slate-800/60 rounded-sm">
      <div>
        <h1 class="text-2xl font-bold text-white tracking-tight uppercase">Network Sentinel</h1>
        <p class="text-xs text-slate-500 mt-1 font-mono uppercase">IDS & Traffic Mapping for K3s Infrastructure</p>
      </div>
      
      <div class="flex flex-wrap items-center gap-4">
        <select v-model="selectedNS" 
                class="bg-[#0b0c10] border border-slate-700 text-[10px] text-slate-300 px-4 py-2 rounded-sm focus:outline-none focus:border-[#f05a28] uppercase font-bold tracking-widest cursor-pointer">
          <option v-for="ns in namespaces" :key="ns" :value="ns">{{ ns }}</option>
        </select>

        <button @click="runQuickAudit" 
                class="bg-blue-500/10 hover:bg-blue-500/20 border border-blue-500 text-blue-500 px-6 py-2 rounded-sm text-[10px] font-bold uppercase tracking-widest transition-all cursor-pointer">
            🔍 Quick Audit
        </button>
        
        <button @click="triggerHarden" 
                class="bg-[#f05a28]/10 hover:bg-[#f05a28]/20 border border-[#f05a28] text-[#f05a28] px-6 py-2 rounded-sm text-[10px] font-bold uppercase tracking-widest transition-all cursor-pointer">
          Deploy Hardening
        </button>
      </div>
    </div>

    <div v-if="edges.length > 0 && !isLoading" class="bg-[#111217] border border-slate-800/60 p-6 rounded-sm">
      <h3 class="text-xs font-bold text-slate-400 mb-6 uppercase tracking-widest flex items-center gap-2">
        <span class="w-2 h-2 bg-blue-500 rounded-full animate-pulse"></span>
        Active Traffic Flows
      </h3>
      <div class="flex flex-wrap justify-center items-center gap-12 py-10">
        <div v-for="edge in edges" :key="edge.source + edge.target" class="flex items-center gap-4">
          <div class="px-4 py-2 bg-blue-900/20 border border-blue-500/30 rounded text-[10px] text-white font-mono">
            {{ edge.source }}
          </div>
          
          <div class="flex flex-col items-center">
            <span class="text-[8px] text-[#f05a28] font-bold animate-pulse mb-1">{{ edge.label }}</span>
            <div class="h-px w-20 bg-gradient-to-r from-blue-500 to-[#f05a28] relative">
              <div class="absolute right-0 -top-1 border-t-4 border-l-4 border-transparent border-l-[#f05a28]"></div>
            </div>
          </div>
          
          <div class="px-4 py-2 bg-[#f05a28]/10 border border-[#f05a28]/30 rounded text-[10px] text-white font-mono">
            {{ edge.target }}
          </div>
        </div>
      </div>
    </div>

    <div v-if="!isLoading" class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
      <div v-for="pod in pods" :key="pod.id" 
           class="bg-[#0d0e12] border border-slate-800/60 p-5 rounded-sm hover:border-blue-500/40 transition-all group relative overflow-hidden">
        
        <div class="flex items-start justify-between mb-4">
          <div class="p-2 bg-blue-600/10 rounded-sm">
            <span class="text-xl">📦</span>
          </div>
          <span :class="['px-2 py-1 text-[8px] font-bold uppercase border rounded-full', getStatusColor(pod.status)]">
            {{ pod.status }}
          </span>
        </div>
        
        <h3 class="text-sm font-bold text-white truncate mb-1 uppercase tracking-tight">{{ pod.name }}</h3>
        <p class="text-[10px] text-slate-500 font-mono mb-4">{{ pod.ip || 'No IP Allocated' }}</p>
        
        <div class="space-y-2 border-t border-slate-800/40 pt-4">
          <div class="flex justify-between text-[9px] uppercase font-bold">
            <span class="text-slate-600">Namespace</span>
            <span class="text-blue-400">{{ pod.namespace }}</span>
          </div>
          <div class="flex flex-wrap gap-1 mt-2">
            <span v-for="(val, key) in pod.labels" :key="key" 
                  class="text-[7px] bg-slate-800/50 text-slate-400 px-1.5 py-0.5 rounded-sm">
              {{ key }}:{{ val }}
            </span>
          </div>
        </div>
      </div>
    </div>

    <div v-else class="flex flex-col justify-center items-center h-64 space-y-4">
      <div class="w-12 h-12 border-2 border-[#f05a28] border-t-transparent rounded-full animate-spin"></div>
      <span class="text-[#f05a28] font-mono uppercase tracking-[0.5em] text-xs">Scanning Cluster Flux...</span>
    </div>
  </div>
</template>

<style scoped>
/* Petit effet de scan sur les cartes au survol */
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
</style>