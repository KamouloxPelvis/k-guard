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

  // État pour l'intégration Webex
  const webexConfig = ref({
    enabled: false,
    token: '',
    room_id: ''
  });

  const debugData = ref<DebugInfo | null>(null);
  const loading = ref(true);
  const purging = ref(false);
  const savingWebex = ref(false);

  const fetchSettings = async () => {
    loading.value = true;
    try {
      // 1. Fetch Storage Info
      const storageRes = await api.get('/k3s/debug/storage');
      debugData.value = storageRes.data;

      // 2. Fetch Webex Config (Depuis ta nouvelle table integrations)
      // On suppose une route GET /api/settings/integrations/webex
      const webexRes = await api.get('/settings/integrations/webex');
      if (webexRes.data) {
        webexConfig.value = {
          enabled: webexRes.data.enabled === 1,
          token: webexRes.data.token || '',
          room_id: webexRes.data.target_id || ''
        };
      }
    } catch (error) {
      console.error("Failed to fetch settings", error);
    } finally {
      loading.value = false;
    }
  };

  onMounted(fetchSettings);

  const handleSaveWebex = async () => {
    savingWebex.value = true;
    try {
      await api.post('/settings/integrations/webex', {
        enabled: webexConfig.value.enabled,
        token: webexConfig.value.token,
        room_id: webexConfig.value.room_id
      });
      alert("✅ Cisco Webex configuration synced with K-Guard DB");
    } catch (error) {
      alert("❌ Failed to sync Webex settings.");
    } finally {
      savingWebex.value = false;
    }
  };

  const handlePurgeCache = async () => {
    if (!confirm("⚠️ WARNING: This will delete all Trivy local databases. Proceed?")) return;
    purging.value = true;
    try {
      const { data } = await api.post('/k3s/debug/purge-cache');
      alert(data.message);
      await fetchSettings();
    } catch (error) {
      alert("Purge failed.");
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
      <button @click="fetchSettings" class="bg-blue-600/10 hover:bg-blue-600/20 border border-blue-500/30 px-4 py-2 rounded-sm text-[10px] font-bold text-blue-400 transition-all uppercase cursor-pointer">
        Refresh Status
      </button>
    </header>

    <div v-if="loading" class="flex flex-col items-center justify-center py-40">
      <div class="w-10 h-10 border-2 border-[#f05a28] border-t-transparent rounded-full animate-spin mb-6"></div>
      <span class="text-[9px] uppercase tracking-[0.5em] text-[#f05a28]">Syncing Ecosystem...</span>
    </div>

    <div v-else class="max-w-5xl mx-auto space-y-8 pb-20">
      
      <div class="bg-[#111217]/80 border border-slate-800 p-8 rounded-sm">
        <h3 class="text-[11px] text-slate-400 uppercase font-black mb-8 tracking-[0.3em] flex items-center gap-2">
          <span class="w-2 h-2 bg-cyan-500 rounded-full shadow-[0_0_8px_rgba(6,182,212,0.6)]"></span>
          External Integrations
        </h3>

        <div class="grid grid-cols-1 gap-6">
          <div class="border border-slate-800 bg-slate-900/30 p-6 rounded-sm flex flex-col md:flex-row gap-8">
            <div class="flex flex-col items-center justify-center min-w-[120px]">
              <img src="/logo_webex.png" alt="Cisco Webex" class="w-16 h-16 object-contain mb-4 grayscale hover:grayscale-0 transition-all duration-500">
              <span class="text-[10px] font-bold text-slate-500 uppercase tracking-widest">Webex API</span>
            </div>

            <div class="flex-1 space-y-4">
              <div class="flex justify-between items-center">
                <h4 class="text-white text-sm font-bold uppercase">Cisco Webex Notifier</h4>
                <label class="relative inline-flex items-center cursor-pointer">
                  <input type="checkbox" v-model="webexConfig.enabled" class="sr-only peer">
                  <div class="w-11 h-6 bg-slate-800 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-slate-400 after:border-slate-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-cyan-600"></div>
                </label>
              </div>

              <div v-if="webexConfig.enabled" class="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div class="space-y-1">
                  <label class="text-[9px] text-slate-500 uppercase font-bold">Bot Access Token</label>
                  <input type="password" v-model="webexConfig.token" placeholder="Bearer..." class="w-full bg-black border border-slate-800 p-2 text-xs text-cyan-400 font-mono focus:border-cyan-500 outline-none">
                </div>
                <div class="space-y-1">
                  <label class="text-[9px] text-slate-500 uppercase font-bold">Target Room ID</label>
                  <input type="text" v-model="webexConfig.room_id" placeholder="Y2lzY29..." class="w-full bg-black border border-slate-800 p-2 text-xs text-cyan-400 font-mono focus:border-cyan-500 outline-none">
                </div>
              </div>

              <div class="flex justify-end pt-2">
                <button 
                  @click="handleSaveWebex" 
                  :disabled="savingWebex || !webexConfig.enabled" 
                  class="text-[10px] font-black uppercase tracking-widest border px-6 py-2 transition-all"
                  :class="[
                    webexConfig.enabled 
                      ? 'text-cyan-500 border-cyan-900/50 hover:bg-cyan-600 hover:text-white cursor-pointer' 
                      : 'text-slate-600 border-slate-800 bg-slate-900/50 cursor-not-allowed opacity-50'
                  ]"
                >
                  {{ savingWebex ? 'Syncing...' : 'Save Configuration' }}
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div v-if="debugData && debugData.disks && Object.keys(debugData.disks).length > 0" 
           class="bg-[#111217]/80 border border-slate-800 p-8 rounded-sm">
        
        <div class="flex flex-col md:flex-row justify-between items-start md:items-center mb-8 gap-6">
          <div>
            <h3 class="text-[11px] text-slate-400 uppercase font-black mb-2 tracking-[0.3em] flex items-center gap-2">
              <span class="w-2 h-2 bg-blue-500 rounded-full shadow-[0_0_8px_rgba(59,130,246,0.6)]"></span>
              Infrastructure Storage
            </h3>
            <div class="flex flex-wrap gap-2 mt-4">
              <span v-for="(_, path) in debugData.disks" :key="path" 
                    class="text-[9px] bg-slate-900 border border-slate-700 px-3 py-1 text-slate-400 font-mono rounded-full uppercase">
                📍 {{ path }}
              </span>
            </div>
          </div>

          <div class="flex items-baseline gap-2">
            <span class="text-5xl font-extralight text-white leading-none">
              {{ Object.values(debugData.disks)[0]?.percent }}%
            </span>
            <span class="text-[10px] text-slate-500 uppercase font-bold tracking-widest">Used</span>
          </div>
        </div>
        
        <div class="relative pt-2">
          <div class="w-full bg-slate-900 h-2 rounded-full overflow-hidden mb-6">
            <div class="h-full transition-all duration-1000 ease-out"
              :class="(Object.values(debugData.disks)[0]?.percent ?? 0) > 85 ? 'bg-red-500 shadow-[0_0_20px_rgba(239,68,68,0.4)]' : 'bg-blue-600 shadow-[0_0_15px_rgba(37,99,235,0.3)]'"
              :style="{ width: `${Object.values(debugData.disks)[0]?.percent ?? 0}%` }">
            </div>
          </div>
          <div class="flex justify-between items-center text-[10px] text-slate-500 font-mono uppercase tracking-[0.1em]">
            <div class="flex gap-6">
              <span>Free space: <b class="text-blue-400">{{ Object.values(debugData.disks)[0]?.free_gb }} GB</b></span>
              <span>Total capacity: {{ Object.values(debugData.disks)[0]?.total_gb }} GB</span>
            </div>
          </div>
        </div>
      </div>

      <div class="bg-[#111217]/80 border border-slate-800 p-8 rounded-sm flex flex-col md:flex-row items-center justify-between gap-6">
        <div class="flex items-center gap-6">
          <div class="text-4xl">🗄️</div>
          <div>
            <h3 class="text-lg text-white font-bold uppercase tracking-tight">K-Guard SQLite Persistence</h3>
            <p class="text-xs text-slate-500 mt-1 uppercase tracking-wider italic">Storing Trivy scan history and security events</p>
          </div>
        </div>
        <div class="flex items-center">
          <span :class="debugData?.database_present ? 'text-green-500 border-green-500/30' : 'text-red-500 border-red-500/30'"
            class="px-6 py-3 border text-[10px] font-black uppercase tracking-[0.2em]">
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
            Flush security metadata and clear Trivy local databases.
          </p>
        </div>
        <button @click="handlePurgeCache" :disabled="purging"
          class="bg-red-600 hover:bg-red-700 disabled:opacity-30 text-white px-8 py-3 rounded-sm text-[10px] font-black uppercase tracking-[0.2em] transition-all">
          {{ purging ? 'Executing Purge...' : 'Purge Cache' }}
        </button>
      </div>

    </div>
  </div>
</template>