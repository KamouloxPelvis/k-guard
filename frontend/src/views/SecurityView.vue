<script setup lang="ts">
  import { ref, onMounted, onUnmounted, computed } from 'vue';
  import api from '@/services/api';

  // --- INTERFACES ---
  interface SecurityAlert {
    id: string;
    source: string;
    severity: string;
    message: string;
    created_at: string;
  }

  // --- REACTIVE STATES ---
  const alerts = ref<SecurityAlert[]>([]);
  const isLoading = ref(true);
  const selectedRange = ref('now-15m'); // Time window for ELK dashboard

  // --- CONFIGURATION ---
  // Base URL from your Share/Embed code (removing the hardcoded time parameters)
  const kibanaBaseUrl = "/kibana/app/dashboards#/view/ea2db5ff-ddd9-41c7-9715-865cfe0a5d35";

  // Computed source that dynamically injects the chosen time range
  const dashboardSrc = computed(() => {
    return `${kibanaBaseUrl}?embed=true&_g=(time:(from:'${selectedRange.value}',to:now))&show-top-menu=false&show-query-input=false&show-time-filter=false`;
  });

  /**
   * Fetches the latest security alerts from the Elasticsearch cluster.
   * Maps raw ES hits to the SecurityAlert interface for the UI.
   */
  const fetchAlerts = async () => {
    try {
      const response = await api.get('/api/security/alerts');
      
      alerts.value = response.data.map((hit: any) => ({
        id: hit._id,
        source: hit._source.container?.name || 'unknown',
        severity: hit._source.priority || 'INFO',
        message: hit._source.output || 'No description available',
        created_at: hit._source['@timestamp']
      }));
    } catch (error) {
      console.error("[K-Guard] Alert Fetch Error:", error);
    } finally {
      isLoading.value = false;
    }
  };

  const activeTab = ref<'dashboard' | 'alerts'>('dashboard');

  // --- LIFECYCLE ---
  let interval: ReturnType<typeof setInterval>;

  onMounted(() => {
    fetchAlerts();
    // Refresh alerts every 30 seconds
    interval = setInterval(fetchAlerts, 30000);
  });

  onUnmounted(() => {
    clearInterval(interval);
  });
  
</script>

<template>
  <div class="p-4 lg:p-6 space-y-6">
    <header class="border-b border-slate-800 pb-4">
      <div class="flex justify-between items-end">
        <div>
          <h1 class="text-xl font-bold tracking-widest uppercase">Security Operations Center</h1>
          <p class="text-[10px] text-slate-500 uppercase tracking-[0.2em]">Real-time Falco & ELK Monitoring</p>
        </div>

        <nav class="flex gap-6">
          <button @click="activeTab = 'dashboard'" 
                  :class="activeTab === 'dashboard' ? 'text-white border-b border-red-500' : 'text-slate-500'"
                  class="text-[10px] uppercase font-bold tracking-widest pb-1 transition-all">
            Dashboard
          </button>
          <button @click="activeTab = 'alerts'" 
                  :class="activeTab === 'alerts' ? 'text-white border-b border-red-500' : 'text-slate-500'"
                  class="text-[10px] uppercase font-bold tracking-widest pb-1 transition-all">
            Live Feed
          </button>
        </nav>
      </div>
    </header>

    <div class="min-h-[600px]">
      
      <div v-if="activeTab === 'dashboard'" class="bg-[#0b0c10] border border-slate-800/60 rounded-sm h-[600px] overflow-hidden animate-in fade-in duration-500">
        <div class="p-2 flex justify-end">
          <select v-model="selectedRange" class="bg-[#111217] border border-slate-700 text-[9px] px-2 py-0.5 rounded uppercase font-bold tracking-widest cursor-pointer text-white">
            <option value="now-15m">Last 15m</option>
            <option value="now-1h">Last 1h</option>
            <option value="now-24h">Last 24h</option>
          </select>
        </div>
        <iframe 
          :src="dashboardSrc" 
          class="w-full h-full border-0"
          title="Runtime Security Dashboard">
        </iframe>
      </div>

      <div v-else class="grid gap-3 animate-in fade-in duration-500">
        <h2 class="text-[9px] font-black text-slate-600 uppercase tracking-[0.2em] mb-2">Live Alert Feed</h2>
        <div v-for="alert in alerts" :key="alert.id" 
             class="bg-[#181b1f] border-l-2 border-red-500 p-4 flex justify-between items-center hover:bg-[#1e2329] transition-all">
          <div>
            <h3 class="font-mono text-sm font-bold text-white">{{ alert.message }}</h3>
            <p class="text-[10px] text-slate-500 uppercase">{{ alert.source }} // {{ alert.created_at }}</p>
          </div>
          <span class="text-[9px] font-bold px-2 py-1 bg-red-900/20 text-red-500 border border-red-500/30">
            {{ alert.severity }}
          </span>
        </div>
        
        <div v-if="!isLoading && alerts.length === 0" class="p-10 text-center text-slate-600 italic">
          System Secure. No active threats detected.
        </div>
      </div>
    </div>
  </div>
</template>