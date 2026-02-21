<script setup lang="ts">
  import { ref, onMounted } from 'vue';
  import api from '@/services/api';

  interface DiskInfo {
    total_gb: number;
    used_gb: number;
    free_gb: number;
    percent: number;
  }

  interface DebugInfo {
    status: string;
    disks: Record<string, DiskInfo>;
    database_present: boolean;
    timestamp: string;
  }

  const debugData = ref<DebugInfo | null>(null);
  const loading = ref(true);
  const purging = ref(false);

  const fetchDebugInfo = async () => {
    loading.value = true;
    try {
      const { data } = await api.get('/k3s/debug/storage');
      debugData.value = data;
    } catch (error) {
      console.error("Failed to fetch debug info", error);
    } finally {
      loading.value = false;
    }
  };

  onMounted(fetchDebugInfo);

  const handlePurgeCache = async () => {
  if (!confirm("⚠️ WARNING: This will delete all Trivy local databases. Next scans will be slower while rebuilding cache. Proceed?")) return;
  
  purging.value = true;
  try {
    const { data } = await api.post('/k3s/debug/purge-cache');
    alert(data.message);
    // On rafraîchit les stats de stockage après la purge
    await fetchDebugInfo();
  } catch (error) {
    alert("Purge failed. Check backend logs.");
  } finally {
    purging.value = false;
  }
};
</script>

<template>
  <div class="p-8 relative z-10 font-sans h-full overflow-y-auto custom-scrollbar">
    <header class="mb-12 flex justify-between items-end border-b border-slate-800/40 pb-8">
      <div>
        <h2 class="text-xl font-extralight text-white tracking-tight uppercase">Control Center</h2>
        <p class="text-[12px] text-slate-500 mt-2 uppercase tracking-[0.5em]">SRE Infrastructure Control & Diagnostics</p>
      </div>
      <button 
        @click="fetchDebugInfo" 
        class="bg-blue-600/10 hover:bg-blue-600/20 border border-blue-500/30 px-4 py-2 rounded-sm text-[10px] font-bold text-blue-400 transition-all uppercase cursor-pointer"
      >
        Refresh Status
      </button>
    </header>

    <div v-if="loading" class="flex flex-col items-center justify-center py-40">
      <div class="w-10 h-10 border-2 border-[#f05a28] border-t-transparent rounded-full animate-spin mb-6"></div>
      <span class="text-[9px] uppercase tracking-[0.5em] text-[#f05a28]">Accessing Kernel Stats...</span>
    </div>

    <div v-else class="max-w-5xl mx-auto space-y-8 pb-20">
      
      <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div v-for="(info, path) in debugData?.disks" :key="path" 
             class="bg-[#111217]/80 border border-slate-800 p-6 rounded-sm hover:border-slate-700 transition-colors">
          <h3 class="text-[10px] text-slate-500 uppercase font-bold mb-4 tracking-widest flex items-center gap-2">
            <span class="w-1.5 h-1.5 bg-blue-500 rounded-full"></span>
            Mount: {{ path }}
          </h3>
          
          <div class="flex items-end gap-2 mb-2">
            <span class="text-3xl font-light text-white">{{ info.percent }}%</span>
            <span class="text-[10px] text-slate-600 mb-1 uppercase font-mono">Capacity Used</span>
          </div>

          <div class="w-full bg-slate-900 h-1.5 rounded-full overflow-hidden mb-4">
            <div 
              class="h-full transition-all duration-1000 ease-out"
              :class="info.percent > 85 ? 'bg-red-500 shadow-[0_0_10px_rgba(239,68,68,0.5)]' : 'bg-blue-500'"
              :style="{ width: `${info.percent}%` }"
            ></div>
          </div>
          
          <div class="flex justify-between text-[9px] text-slate-500 font-mono uppercase">
            <span>Free: {{ info.free_gb }} GB</span>
            <span>Total: {{ info.total_gb }} GB</span>
          </div>
        </div>
      </div>

      <div class="bg-[#111217]/80 border border-slate-800 p-8 rounded-sm flex flex-col md:flex-row items-center justify-between gap-6">
        <div class="flex items-center gap-6">
          <div class="text-4xl">🗄️</div>
          <div>
            <h3 class="text-lg text-white font-bold uppercase tracking-tight">K-Guard SQLite Persistence</h3>
            <p class="text-xs text-slate-500 mt-1 uppercase tracking-wider italic">
              Storing Trivy scan history and security events
            </p>
          </div>
        </div>
        
        <div class="flex items-center">
          <span 
            :class="debugData?.database_present ? 'bg-green-500/10 text-green-500 border-green-500/30' : 'bg-red-500/10 text-red-500 border-red-500/30'"
            class="px-6 py-3 border text-[10px] font-black uppercase tracking-[0.2em] shadow-sm"
          >
            {{ debugData?.database_present ? '● DB CONNECTED' : '○ DB DISCONNECTED' }}
          </span>
        </div>
      </div>

      <div class="mt-12 p-8 border border-red-900/30 bg-red-950/5 rounded-sm flex flex-col md:flex-row items-center justify-between gap-6">
        <div>
          <h3 class="text-sm text-red-500 font-bold uppercase tracking-[0.2em] flex items-center gap-2">
            <span class="animate-pulse">⚠️</span> Danger Zone
          </h3>
          <p class="text-[10px] text-slate-500 mt-2 uppercase tracking-wide leading-relaxed">
            Flush security metadata, clear Trivy local databases and purge temporary filesystem artifacts. <br/>
            <span class="text-red-900/60 italic">Next scans will require full database synchronization.</span>
          </p>
        </div>
        
        <button 
          @click="handlePurgeCache" 
          :disabled="purging"
          class="w-full md:w-auto bg-red-600 hover:bg-red-700 disabled:opacity-30 disabled:cursor-not-allowed text-white px-8 py-3 rounded-sm text-[10px] font-black uppercase tracking-[0.2em] transition-all duration-300 shadow-lg shadow-red-900/20 cursor-pointer"
        >
          {{ purging ? 'Executing Purge...' : 'Purge Cache' }}
        </button>
      </div>

    </div>
  </div>
</template>