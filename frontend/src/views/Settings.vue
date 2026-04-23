<script setup lang="ts">
  import { ref, onMounted } from 'vue';
  import api from '@/services/api';

  // --- INTERFACES ---
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

  interface WebexIntegration {
    enabled: boolean;
    configured: boolean;
    room_id?: string;
  }

  // --- REACTIVE STATE ---
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
    
    // 1. Fetch infrastructure storage stats
    api.get<DebugInfo>('/k3s/debug/storage')
      .then(res => { debugData.value = res.data; })
      .catch(() => { console.warn("[K-Guard] Infrastructure diagnostics unavailable"); });

    // 2. Fetch Cisco Webex integration status
    try {
      const { data } = await api.get<WebexIntegration>('/settings/integrations/webex');
      if (data && data.configured) {
        isAlreadyConfigured.value = true;
        webexConfig.value = {
          enabled: data.enabled,
          token: '', // Security: token is never retrieved from backend
          room_id: data.room_id || ''
        };
      }
    } catch (error) {
      console.error("[K-Guard] Webex sync failure", error);
    } finally {
      loading.value = false;
    }
  };

  /**
   * Persists Webex Bot configuration to the K-Guard database.
   * Required for real-time security alerts via Cisco Webex Teams.
   */
  const handleSaveWebex = async () => {
    savingWebex.value = true;
    try {
      await api.post('/settings/integrations/webex', {
        enabled: webexConfig.value.enabled,
        token: webexConfig.value.token,
        room_id: webexConfig.value.room_id
      });
      isAlreadyConfigured.value = true;
      alert("✅ Cisco Webex configuration synced.");
    } catch (error) {
      alert("❌ Sync failed. Check logs.");
    } finally {
      savingWebex.value = false;
    }
  };

  /**
   * SRE maintenance action: Clears local vulnerability databases to free up PVC space.
   */
  const handlePurgeCache = async () => {
    if (!confirm("⚠️ Purge local Trivy databases? This operation is irreversible.")) return;
    purging.value = true;
    try {
      const { data } = await api.post<{ message: string }>('/k3s/debug/purge-cache', {});
      alert(data.message);
      await fetchSettings();
    } catch (error) {
      alert("Purge operation failed.");
    } finally {
      purging.value = false;
    }
  };

  onMounted(fetchSettings);
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
      
      <div class="bg-[#111217]/80 border border-slate-800 p-5 rounded-sm shadow-xl">
        <div class="flex justify-between items-center mb-6">
          <h3 class="text-[10px] text-slate-400 uppercase font-black tracking-[0.2em] flex items-center gap-2">
            <span class="w-1.5 h-1.5 bg-cyan-500 rounded-full shadow-[0_0_8px_rgba(6,182,212,0.6)]"></span>
            External Integrations
          </h3>
          <span v-if="isAlreadyConfigured" class="text-[8px] px-2 py-0.5 bg-cyan-500/10 border border-cyan-500/30 text-cyan-400 font-bold rounded-sm">
            ● LINKED TO WEBEX
          </span>
        </div>

        <div class="border border-slate-800 bg-slate-900/30 p-4 rounded-sm flex flex-col md:flex-row gap-6">
          <div class="flex flex-col items-center justify-center min-w-[100px]">
            <div class="w-12 h-12 bg-white/5 rounded-lg flex items-center justify-center mb-2">
              <span class="text-xl">📡</span>
            </div>
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
                <input type="password" v-model="webexConfig.token" placeholder="Enter Bot Bearer Token..." class="w-full bg-black border border-slate-800 p-1.5 text-[11px] text-cyan-400 font-mono focus:border-cyan-500 outline-none">
              </div>
              <div class="space-y-1">
                <label class="text-[8px] text-slate-500 uppercase font-bold">Room ID</label>
                <input type="text" v-model="webexConfig.room_id" placeholder="Enter Destination Room ID..." class="w-full bg-black border border-slate-800 p-1.5 text-[11px] text-cyan-400 font-mono focus:border-cyan-500 outline-none">
              </div>
            </div>

            <div class="flex justify-end pt-1">
              <button @click="handleSaveWebex" :disabled="savingWebex || !webexConfig.enabled" 
                class="text-[9px] font-black uppercase tracking-widest border px-4 py-1.5 transition-all cursor-pointer"
                :class="[webexConfig.enabled ? 'text-cyan-500 border-cyan-900/50 hover:bg-cyan-600 hover:text-white' : 'text-slate-600 border-slate-800 opacity-50']">
                {{ savingWebex ? 'Syncing...' : (isAlreadyConfigured ? 'Update Integration' : 'Enable Bot') }}
              </button>
            </div>
          </div>
        </div>
      </div>

      <div v-if="debugData && debugData.disks" class="bg-[#111217]/80 border border-slate-800 p-5 rounded-sm">
        <div class="flex justify-between items-center mb-4">
          <h3 class="text-[10px] text-slate-400 uppercase font-black tracking-[0.2em] flex items-center gap-2">
            <span class="w-1.5 h-1.5 bg-blue-500 rounded-full shadow-[0_0_8px_rgba(59,130,246,0.6)]"></span>
            Infrastructure Storage
          </h3>
          <span class="text-2xl font-extralight text-white">
            {{ Object.values(debugData.disks)[0]?.percent ?? 0 }}%
          </span>
        </div>
        
        <div class="relative pt-1">
          <div class="w-full bg-slate-900 h-1.5 rounded-full overflow-hidden mb-3">
            <div class="h-full transition-all duration-1000 ease-out"
              :class="(Object.values(debugData.disks)[0]?.percent ?? 0) > 85 ? 'bg-red-500' : 'bg-blue-600'"
              :style="{ width: `${Object.values(debugData.disks)[0]?.percent ?? 0}%` }">
            </div>
          </div>
          <div class="flex justify-between text-[9px] text-slate-600 font-mono uppercase">
            <span>Free: <b class="text-blue-400">{{ Object.values(debugData.disks)[0]?.free_gb ?? 0 }} GB</b></span>
            <span>Path: {{ Object.keys(debugData.disks)[0] || '/' }}</span>
          </div>
        </div>
      </div>

      <div class="p-5 border border-red-900/30 bg-red-950/5 rounded-sm flex flex-col md:flex-row items-center justify-between gap-4">
        <div>
          <h3 class="text-xs text-red-500 font-bold uppercase tracking-[0.2em]">Maintenance Mode</h3>
          <p class="text-[9px] text-slate-600 mt-1 uppercase leading-relaxed">
            Reset local vulnerability cache and clear historical events.
          </p>
        </div>
        <button @click="handlePurgeCache" :disabled="purging"
          class="bg-red-600/90 hover:bg-red-700 disabled:opacity-30 text-white px-6 py-2 rounded-sm text-[9px] font-black uppercase tracking-widest transition-all">
          {{ purging ? 'Executing...' : 'Purge All Caches' }}
        </button>
      </div>

    </div>
  </div>
</template>