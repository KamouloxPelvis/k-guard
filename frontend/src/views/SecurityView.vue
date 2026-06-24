<script setup lang="ts">
  import { ref, onMounted } from 'vue';
  import api from '@/services/api';

  // --- INTERFACES ---
  interface SecurityAlert {
    id: number;
    source: string;
    severity: string;
    message: string;
    created_at: string;
  }

  // --- REACTIVE STATES ---
  const alerts = ref<SecurityAlert[]>([]);
  const isLoading = ref(true);

  /**
   * Fetches the latest security alerts from the database.
   * This replaces the old Trivy scan polling.
   */
  const fetchAlerts = async () => {
    try {
      // Tu créeras bientôt cette route pour récupérer les alertes stockées
      const response = await api.get<SecurityAlert[]>('/api/security/alerts');
      alerts.value = response.data;
    } catch (error) {
      console.error("[K-Guard] Alert Fetch Error:", error);
    } finally {
      isLoading.value = false;
    }
  };

  onMounted(fetchAlerts);
</script>

<template>
  <div class="p-4 lg:p-6 relative z-10 font-sans text-slate-300">
    <header class="mb-6 border-b border-slate-800 pb-4">
      <h1 class="text-xl font-bold tracking-widest uppercase">Security Operations Center</h1>
      <p class="text-[10px] text-slate-500 uppercase tracking-[0.2em]">Real-time Falco & Wazuh Monitoring</p>
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