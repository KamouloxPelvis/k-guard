<script setup lang="ts">
  import { ref, onMounted, onUnmounted } from 'vue';
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

  /**
   * Fetches the latest security alerts from the Elasticsearch cluster.
   * Maps raw ES hits to the SecurityAlert interface for the UI.
   */
  const fetchAlerts = async () => {
    try {
      const response = await api.get('/api/security/alerts');
      
      // Mapping raw Elasticsearch hits to the SecurityAlert structure
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

  let interval: ReturnType<typeof setInterval>;

  onMounted(() => {
    fetchAlerts();
    // Rafraîchissement toutes les 30 secondes
    interval = setInterval(fetchAlerts, 30000);
  });

  onUnmounted(() => {
    clearInterval(interval);
  });
</script>

<template>
  <div class="p-4 lg:p-6 relative z-10 font-sans text-slate-300">
    <header class="mb-6 border-b border-slate-800 pb-4">
      <h1 class="text-xl font-bold tracking-widest uppercase">Security Operations Center</h1>
      <p class="text-[10px] text-slate-500 uppercase tracking-[0.2em]">Real-time Falco & ELK Monitoring</p>
    </header>

    <div class="grid gap-3">
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
</template>