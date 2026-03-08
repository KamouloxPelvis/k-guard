<script setup lang="ts">
  import { ref, onMounted, onUnmounted } from 'vue';
  import api from '@/services/api';

  // --- Interfaces ---
  interface PodStatus {
    name: string;      
    pod_name: string;  
    status: string;    
    ip: string;        
    type: string;
    namespace: string;      
  }

  interface PodMetrics {
    pod_name: string;
    cpuUsage: number;    // Millicores (m)
    memoryUsage: number; // MegaBytes (MiB)
  }

  // --- Reactive State ---
  const apps = ref<PodStatus[]>([]);
  // Retrieve the username from local storage to fix the "Property does not exist" error
  const username = ref<string>(localStorage.getItem('admin_username') || 'Operator');
  const metrics = ref<Record<string, PodMetrics>>(
    JSON.parse(localStorage.getItem('kguard_metrics') || '{}')
  );
  const metricsLoading = ref<Record<string, boolean>>({});
  const loading = ref(false);
  const isInitialLoad = ref(true);
  const selectedPod = ref<PodStatus | null>(null);
  const podLogs = ref("");
  const showModal = ref(false);
  let refreshInterval: any = null;

  const nodeCapacity = ref({ 
    cpu_cores: 2, 
    memory_total_ki: 8388608 
  });

  // --- Data Fetching Logic ---
  
  const fetchNodeCapacity = async () => {
    try {
      const { data } = await api.get('/k3s/node-capacity');
      nodeCapacity.value = data;
    } catch (error) {
      console.warn("⚠️ Node capacity failed, using fallback: 2 vCPU/8GB");
    }
  };

  const fetchMetrics = async (namespace: string) => {
    if (isInitialLoad.value) metricsLoading.value[namespace] = true;
    try {
      const { data } = await api.get(`/k3s/metrics/${namespace}`);
      if (Array.isArray(data)) {
        data.forEach((m: PodMetrics) => { 
          metrics.value[m.pod_name] = m; 
        });
        localStorage.setItem('kguard_metrics', JSON.stringify(metrics.value));
      }
    } catch (e) { 
      console.error("Metrics sync error", e); 
    } finally { 
      metricsLoading.value[namespace] = false; 
    }
  };

  const fetchClusterData = async () => {
    loading.value = true; 
    apps.value = [];
    
    try {
      const { data } = await api.get('/k3s/cluster-status');
      if (Array.isArray(data)) {
        apps.value = data;
        const namespaces = [...new Set(data.map((p: PodStatus) => p.namespace))];
        namespaces.forEach(ns => fetchMetrics(ns as string));
      }
    } catch (error: any) {
      console.error("Cluster data sync error", error);
    } finally {
      setTimeout(() => {
        loading.value = false;
        isInitialLoad.value = false;
      }, 500);
    }
  };

  // --- Calculations ---
  
  const calculateCpuPercent = (raw: any): number => {
    if (!raw) return 0;
    const millicores = typeof raw === 'string' ? parseInt(raw) : raw;
    const totalMillicores = nodeCapacity.value.cpu_cores * 1000;
    return (millicores / totalMillicores) * 100;
  };

  const calculateMemPercent = (raw: any): number => {
    if (!raw) return 0;
    const mibValue = typeof raw === 'string' ? parseInt(raw) : raw;
    const totalMib = nodeCapacity.value.memory_total_ki / 1024;
    return Math.min((mibValue / totalMib) * 100, 100);
  };

  const formatMemory = (raw: any): string => {
    if (!raw) return '0 MB';
    const mibValue = typeof raw === 'string' ? parseInt(raw) : raw;
    return mibValue < 1024 ? `${mibValue} MB` : `${(mibValue / 1024).toFixed(2)} GB`;
  };

  // --- UI Actions ---
  
  const openDetails = async (pod: PodStatus) => {
    selectedPod.value = pod;
    showModal.value = true;
    podLogs.value = ">> ESTABLISHING SECURE CONNECTION...";
    try {
      const { data } = await api.get(`/k3s/logs/${pod.namespace}/${pod.pod_name}`);
      podLogs.value = data.logs || "No logs available for this instance.";
    } catch (error) { 
      podLogs.value = "CRITICAL ERROR: Connection refused by API."; 
    }
  };

  const restartPod = async (event: Event, pod: PodStatus) => {
    event.stopPropagation(); 
    if (!confirm(`CAUTION: Trigger Rolling Update for ${pod.name}?`)) return;
    try {
      await api.post(`/remediation/restart/${pod.namespace}/${pod.name}`);
      fetchClusterData(); 
    } catch (error) { 
      alert("Action failed: Could not patch deployment."); 
    }
  };

  const remediateLoad = async (event: Event, pod: PodStatus) => {
    event.stopPropagation();
    if (!confirm(`ACTIVATE SRE REMEDIATION: Scale down ${pod.name}?`)) return;
    try {
      await api.post(`/remediation/remediate/${pod.namespace}/${pod.pod_name}`);
      alert("Remediation signal dispatched.");
    } catch (error) { 
      alert("Remediation failure."); 
    }
  };

  const getStatusClass = (status: string) => {
    const s = (status || 'UNKNOWN').toUpperCase();
    return (s === 'SECURE' || s === 'RUNNING') 
      ? 'text-green-500 bg-green-500/10 border-green-500/20' 
      : (s === 'STABILIZING' ? 'text-blue-400 bg-blue-500/10 border-blue-500/20' : 'text-red-500 bg-red-500/10 border-red-500/20');
  };

  onMounted(() => {
    fetchNodeCapacity();
    fetchClusterData();
    refreshInterval = setInterval(fetchClusterData, 15000);
  });

  onUnmounted(() => { 
    if (refreshInterval) clearInterval(refreshInterval); 
  });
</script>

<template>
  <div class="p-4 lg:p-6 relative z-10">
    
    <header class="mb-4 flex justify-between items-center border-b border-slate-800/40 pb-3">
      <div>
        <p class="text-[10px] text-slate-500 uppercase tracking-[0.4em]">K-Guard SRE Monitor</p>
      </div>
      <div class="flex gap-3">
        <button @click="fetchClusterData" class="bg-slate-800/40 hover:bg-blue-600 border border-slate-700 px-4 py-1.5 rounded-sm transition-all text-[9px] font-bold text-slate-400 hover:text-white uppercase tracking-widest cursor-pointer">
          ReSync
        </button>
      </div>
    </header>

    <div v-if="loading" class="flex flex-col items-center justify-center py-24">
      <div class="w-8 h-8 border-2 border-blue-500 border-t-transparent rounded-full animate-spin mb-4"></div>
      <span class="text-[8px] uppercase tracking-[0.4em] text-blue-500">Scanning Nodes...</span>
    </div>

    <div v-else class="grid grid-cols-1 xl:grid-cols-2 gap-4 max-w-7xl mx-auto">
      <div v-for="pod in apps" :key="pod.pod_name" @click="openDetails(pod)"
          class="group relative bg-[#181b1f]/60 backdrop-blur-sm border border-slate-800 p-4 rounded-sm hover:border-blue-500/40 transition-all cursor-pointer">
        
        <div class="absolute top-0 left-0 w-1 h-full" 
            :class="pod.status === 'SECURE' || pod.status === 'RUNNING' ? 'bg-green-500' : 'bg-red-500'">
        </div>
        
        <div class="flex justify-between items-start mb-4">
          <div class="flex flex-col">
            <h3 class="text-md font-bold text-white uppercase leading-tight tracking-tight">{{ pod.name }}</h3>
            <p class="text-[9px] text-slate-400 font-mono opacity-80">NS: {{ pod.namespace }}</p>
          </div>
          <span :class="getStatusClass(pod.status)" class="text-[7px] font-black px-1.5 py-0.5 border rounded-sm uppercase">
            {{ pod.status }}
          </span>
        </div>

        <div class="space-y-3 mb-4">
          <div class="flex flex-col gap-1.5">
            <div class="flex justify-between text-[9px] uppercase font-bold tracking-wider">
              <span class="text-slate-500">CPU Usage</span>
              <span v-if="metricsLoading[pod.namespace]" class="text-blue-500 animate-pulse">[ SCANNING... ]</span>
              <span class="text-blue-400 font-mono">{{ calculateCpuPercent(metrics[pod.pod_name]?.cpuUsage).toFixed(1) }}%</span>
            </div>
            <div class="w-full bg-slate-900 h-1 rounded-full overflow-hidden">
              <div class="h-full transition-all duration-1000"
                :class="calculateCpuPercent(metrics[pod.pod_name]?.cpuUsage) > 60 ? 'bg-red-600' : 'bg-blue-500'"
                :style="{ width: `${calculateCpuPercent(metrics[pod.pod_name]?.cpuUsage)}%` }">
              </div>
            </div>
          </div>

          <div class="flex flex-col gap-1.5">
            <div class="flex justify-between text-[9px] uppercase font-bold tracking-wider">
              <span class="text-slate-500">RAM</span>
              <span class="text-indigo-400 font-mono text-[10px]">{{ formatMemory(metrics[pod.pod_name]?.memoryUsage) }}</span>
            </div>
            <div class="w-full h-1 bg-slate-900 rounded-full overflow-hidden">
              <div class="h-full bg-indigo-500 transition-all duration-1000" 
                  :style="{ width: calculateMemPercent(metrics[pod.pod_name]?.memoryUsage) + '%' }"></div>
            </div>
          </div>
        </div>

        <div class="flex justify-between items-center bg-black/20 p-1.5 border border-slate-800/50 mb-3 font-mono">
          <span class="text-[9px] text-slate-500 uppercase font-bold">Virtual IP</span>
          <span class="text-[11px] text-blue-300">{{ pod.ip }}</span>
        </div>

        <div class="flex justify-between items-center pt-3 border-t border-slate-800/30">
          <button @click.stop="(e) => restartPod(e, pod)" class="px-2 py-1 text-[9px] font-bold uppercase border border-red-500/40 text-red-500 hover:bg-red-500 hover:text-white transition-all rounded-sm">
            Restart
          </button>
          <div class="flex gap-2">
            <button @click.stop="openDetails(pod)" class="text-[9px] px-2 py-1 bg-slate-800 hover:bg-slate-700 text-slate-300 uppercase font-bold transition-all border border-slate-700">Logs</button>
            <button v-if="calculateCpuPercent(metrics[pod.pod_name]?.cpuUsage) > 30" 
                    @click.stop="(e) => remediateLoad(e, pod)" 
                    class="text-[9px] px-2 py-1 bg-orange-500/10 hover:bg-orange-600 text-orange-500 hover:text-white uppercase font-bold transition-all border border-orange-500/30">
              SRE
            </button>
          </div>
        </div>
      </div>
    </div>

    <Teleport to="body">
      <div v-if="showModal" class="fixed inset-0 z-[100] flex items-center justify-center p-4 bg-black/95 backdrop-blur-md">
        <div class="bg-[#0d0e12] border border-slate-800 w-full max-w-5xl h-[85vh] flex flex-col rounded-sm">
          <div class="p-3 border-b border-slate-800 flex justify-between items-center bg-[#181b1f]">
            <span class="text-[9px] font-mono text-blue-400 uppercase tracking-widest">Secure Console // {{ selectedPod?.pod_name }}</span>
            <button @click="showModal = false" class="text-slate-500 hover:text-white text-xl">&times;</button>
          </div>
          <div class="flex-1 p-4 overflow-y-auto font-mono text-[11px] text-blue-100/80 bg-black/40">
            <pre class="whitespace-pre-wrap">{{ podLogs }}</pre>
          </div>
          <div class="p-2 border-t border-slate-900 bg-black/40 flex justify-between items-center">
            <span class="text-[7px] text-slate-600 uppercase font-bold">K-Guard Terminal v2.0</span>
            <span class="text-[7px] text-blue-900 font-mono">Operator @ {{ username }}</span>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>