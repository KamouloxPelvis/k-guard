<script setup lang="ts">
  import { ref, onMounted } from 'vue';
  import api from '@/services/api';

  interface DiskInfo {
    total_gb: number; used_gb: number; free_gb: number; percent: number;
  }

  interface DebugInfo {
    status: string;
    disks: Record<string, DiskInfo>;
    database_present: boolean;
    timestamp: string;
  }

  // --- External Integration State (Cisco Webex) ---
  const webexConfig = ref({
    enabled: false,
    token: '',
    room_id: ''
  });

  const debugData = ref<DebugInfo | null>(null);
  const loading = ref(true);
  const purging = ref(false);
  const savingWebex = ref(false);
  const isAlreadyConfigured = ref(false);

 /**
  * Synchronizes infrastructure diagnostics and integration settings.
  */
 const fetchSettings = async () => {
  loading.value = true;
  
  // 1. Fetch infrastructure storage stats in background
  api.get('/k3s/debug/storage')
    .then(res => { debugData.value = res.data; })
    .catch(_ => { console.warn("Infrastructure diagnostics unavailable"); });

  // 2. Fetch Cisco Webex integration status
  try {
    const webexRes = await api.get('/settings/integrations/webex');
    if (webexRes.data && webexRes.data.configured) {
      isAlreadyConfigured.value = true;
      webexConfig.value = {
        enabled: webexRes.data.enabled,
        token: '', // Token is never sent back for security reasons
        room_id: webexRes.data.room_id || ''
      };
    }
  } catch (error) {
    console.error("Webex synchronization error", error);
  } finally {
    loading.value = false;
  }
};

onMounted(() => {
  fetchSettings();
});

/**
 * Persists Webex Bot configuration to the K-Guard database.
 */
const handleSaveWebex = async () => {
  savingWebex.value = true;
  try {
    await api.post('/settings/integrations/webex', {
      enabled: webexConfig.value.enabled,
      token: webexConfig.value.token,
      room_id: webexConfig.value.room_id
    });
    // Update local UI state after successful persistence
    isAlreadyConfigured.value = true;
    alert("✅ Cisco Webex configuration synced with K-Guard DB");
  } catch (error) {
    alert("❌ Failed to sync Webex settings. Check API logs.");
  } finally {
    savingWebex.value = false;
  }
};

  /**
   * SRE maintenance action: Clears local Trivy databases on the PVC.
   */
  const handlePurgeCache = async () => {
    if (!confirm("⚠️ WARNING: This will delete all Trivy local databases. Proceed?")) return;
    purging.value = true;
    try {
      const { data } = await api.post('/k3s/debug/purge-cache');
      alert(data.message);
      await fetchSettings();
    } catch (error) {
      alert("Purge operation failed.");
    } finally {
      purging.value = false;
    }
  };
</script>

<template>
  <div class="p-4 lg:p-6 relative z-10 font-sans h-full overflow-y-auto custom-scrollbar">
    
    <header class="mb-4 flex justify-between items-end border-b border-slate-800/40 pb-3">
      <div>
        <p class="text-[10px] text-slate-500 mt-2 uppercase tracking-[0.4em]">SRE Infrastructure Control & Diagnostics</p>
      </div>
      <button @click="fetchSettings" class="bg-blue-600/10 hover:bg-blue-600/20 border border-blue-500/30 px-3 py-1.5 rounded-sm text-[9px] font-bold text-blue-400 transition-all uppercase cursor-pointer">
        Refresh
      </button>
    </header>

    <div v-if="loading" class="flex flex-col items-center justify-center py-20">
      <div class="w-8 h-8 border-2 border-[#f05a28] border-t-transparent rounded-full animate-spin mb-4"></div>
      <span class="text-[8px] uppercase tracking-[0.4em] text-[#f05a28]">Syncing Ecosystem...</span>
    </div>

    <div v-else class="max-w-5xl mx-auto space-y-4 pb-10">
      
      <div class="bg-[#111217]/80 border border-slate-800 p-5 rounded-sm">
        <div class="flex justify-between items-center mb-6">
          <h3 class="text-[10px] text-slate-400 uppercase font-black tracking-[0.2em] flex items-center gap-2">
            <span class="w-1.5 h-1.5 bg-cyan-500 rounded-full shadow-[0_0_8px_rgba(6,182,212,0.6)]"></span>
            External Integrations
          </h3>
          <span v-if="isAlreadyConfigured" class="text-[8px] px-2 py-0.5 bg-cyan-500/10 border border-cyan-500/30 text-cyan-400 font-bold rounded-sm animate-pulse">
            ● LINKED TO WEBEX
          </span>
        </div>

        <div class="grid grid-cols-1 gap-4">
          <div class="border border-slate-800 bg-slate-900/30 p-4 rounded-sm flex flex-col md:flex-row gap-6">
            <div class="flex flex-col items-center justify-center min-w-[100px]">
              <img src="/logo_webex.png" alt="Cisco Webex" class="w-12 h-12 object-contain mb-2" :class="webexConfig.enabled ? 'grayscale-0' : 'grayscale'">
              <span class="text-[9px] font-bold text-slate-600 uppercase tracking-widest">Webex API</span>
            </div>

            <div class="flex-1 space-y-3">
              <div class="flex justify-between items-center">
                <h4 class="text-white text-xs font-bold uppercase">Cisco Webex Notifier</h4>
                <label class="relative inline-flex items-center cursor-pointer scale-90">
                  <input type="checkbox" v-model="webexConfig.enabled" class="sr-only peer">
                  <div class="w-10 h-5 bg-slate-800 rounded-full peer peer-checked:after:translate-x-full peer-checked:bg-cyan-600 after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-slate-400 after:rounded-full after:h-4 after:w-4 after:transition-all"></div>
                </label>
              </div>

              <div v-if="webexConfig.enabled" class="grid grid-cols-1 md:grid-cols-2 gap-3">
                <div class="space-y-1">
                  <label class="text-[8px] text-slate-500 uppercase font-bold">Bot Token</label>
                  <input type="password" v-model="webexConfig.token" placeholder="Bearer..." class="w-full bg-black border border-slate-800 p-1.5 text-[11px] text-cyan-400 font-mono focus:border-cyan-500 outline-none">
                </div>
                <div class="space-y-1">
                  <label class="text-[8px] text-slate-500 uppercase font-bold">Room ID</label>
                  <input type="text" v-model="webexConfig.room_id" placeholder="Y2lzY29..." class="w-full bg-black border border-slate-800 p-1.5 text-[11px] text-cyan-400 font-mono focus:border-cyan-500 outline-none">
                </div>
              </div>

              <div class="flex justify-end pt-1">
                <button 
                  @click="handleSaveWebex" 
                  :disabled="savingWebex || !webexConfig.enabled" 
                  class="text-[9px] font-black uppercase tracking-widest border px-4 py-1.5 transition-all cursor-pointer"
                  :class="[webexConfig.enabled ? 'text-cyan-500 border-cyan-900/50 hover:bg-cyan-600 hover:text-white' : 'text-slate-600 border-slate-800 opacity-50']"
                >
                  {{ savingWebex ? 'Syncing...' : (isAlreadyConfigured ? 'Update Webex' : 'Save Config') }}
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div v-if="debugData && debugData.disks && Object.keys(debugData.disks).length > 0" 
           class="bg-[#111217]/80 border border-slate-800 p-5 rounded-sm">
        
        <div class="flex flex-col md:flex-row justify-between items-start md:items-center mb-4 gap-4">
          <div>
            <h3 class="text-[10px] text-slate-400 uppercase font-black mb-1 tracking-[0.2em] flex items-center gap-2">
              <span class="w-1.5 h-1.5 bg-blue-500 rounded-full shadow-[0_0_8px_rgba(59,130,246,0.6)]"></span>
              Infrastructure Storage
            </h3>
            <div class="flex flex-wrap gap-1.5 mt-2">
              <span v-for="(_, path) in debugData.disks" :key="path" 
                    class="text-[8px] bg-slate-900 border border-slate-700 px-2 py-0.5 text-slate-500 font-mono rounded-full uppercase">
                📍 {{ path }}
              </span>
            </div>
          </div>

          <div class="flex items-baseline gap-1">
            <span class="text-3xl font-extralight text-white leading-none">
              {{ Object.values(debugData.disks)[0]?.percent }}%
            </span>
            <span class="text-[9px] text-slate-500 uppercase font-bold tracking-widest">Used</span>
          </div>
        </div>
        
        <div class="relative pt-1">
          <div class="w-full bg-slate-900 h-1.5 rounded-full overflow-hidden mb-3">
            <div class="h-full transition-all duration-1000 ease-out"
              :class="(Object.values(debugData.disks)[0]?.percent ?? 0) > 85 ? 'bg-red-500' : 'bg-blue-600'"
              :style="{ width: `${Object.values(debugData.disks)[0]?.percent ?? 0}%` }">
            </div>
          </div>
          <div class="flex justify-between items-center text-[9px] text-slate-600 font-mono uppercase">
            <span>Free: <b class="text-blue-400">{{ Object.values(debugData.disks)[0]?.free_gb }} GB</b></span>
            <span>Total: {{ Object.values(debugData.disks)[0]?.total_gb }} GB</span>
          </div>
        </div>
      </div>

      <div class="bg-[#111217]/80 border border-slate-800 p-4 rounded-sm flex flex-col md:flex-row items-center justify-between gap-4">
        <div class="flex items-center gap-4">
          <div class="text-2xl opacity-50">🗄️</div>
          <div>
            <h3 class="text-sm text-white font-bold uppercase tracking-tight">K-Guard Persistence</h3>
            <p class="text-[9px] text-slate-600 mt-0.5 uppercase tracking-wider italic">SQLite events & scan history</p>
          </div>
        </div>
        <div class="flex items-center">
          <span :class="debugData?.database_present ? 'text-green-500 border-green-500/30' : 'text-red-500 border-red-500/30'"
            class="px-4 py-2 border text-[9px] font-black uppercase tracking-widest">
            {{ debugData?.database_present ? '● DB CONNECTED' : '○ DB DISCONNECTED' }}
          </span>
        </div>
      </div>

      <div class="p-5 border border-red-900/30 bg-red-950/5 rounded-sm flex flex-col md:flex-row items-center justify-between gap-4">
        <div>
          <h3 class="text-xs text-red-500 font-bold uppercase tracking-[0.2em] flex items-center gap-2">
            <span class="animate-pulse">⚠️</span> WARNING
          </h3>
          <p class="text-[9px] text-slate-600 mt-1 uppercase leading-relaxed">
            Flush metadata and clear Trivy local databases.
          </p>
        </div>
        <button @click="handlePurgeCache" :disabled="purging"
          class="bg-red-600/90 hover:bg-red-700 disabled:opacity-30 text-white px-6 py-2 rounded-sm text-[9px] font-black uppercase tracking-widest transition-all">
          {{ purging ? 'Executing...' : 'Purge Cache' }}
        </button>
      </div>

    </div>
  </div>
</template>