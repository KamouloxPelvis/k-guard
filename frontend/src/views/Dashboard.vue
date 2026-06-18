<script setup lang="ts">
  import { ref, computed, onMounted, onUnmounted } from 'vue';
  import { useRoute, useRouter } from 'vue-router';
  import api from '@/services/api';

  interface SystemInfo {
    cluster_version: string;
    vps_os: string;
    uptime: string;
    status: string;
  }
  
  const systemData = ref<SystemInfo | null>(null);
  const systemLatency = ref<number>(0);
  const username = ref<string>(localStorage.getItem('admin_username') || 'Authorized User');
  const isMenuOpen = ref(false);
  const route = useRoute();
  const router = useRouter();
  let statsInterval: any = null;

  /**
   * Health check heartbeat and latency measurement.
   * Calculates the round-trip time (RTT) to the backend health endpoint.
   */
  const updateSystemStats = async () => {
    const start = Date.now();
    try {
      /**
       * The api.get method returns both data and status code.
       * 200 OK confirms backend reachability.
       */
      const response = await api.get('/health');
      if (response.status === 200) {
        systemLatency.value = Date.now() - start;
      }
    } catch (e) {
      systemLatency.value = 0;
      console.warn("[K-Guard] Connectivity lost with backend heartbeat service");
    }
  };

  /**
   * Data retrieval for core infrastructure status.
   * Fetches K3s cluster version and host OS details.
   */
  const fetchSystemInfo = async () => {
    try {
      const { data } = await api.get<SystemInfo>('/k3s/status');
      systemData.value = data;
    } catch (error) {
      /**
       * Errors are logged to the console for infrastructure monitoring.
       * The UI handles null systemData gracefully via templates.
       */
      console.error("Dashboard Service: Failed to retrieve cluster status", error);
    }
  };

  /**
   * Session termination logic.
   * Clears security tokens and user metadata from local storage before redirecting.
   */
  const handleLogout = () => {
    localStorage.removeItem('user_token');
    localStorage.removeItem('admin_username'); 
    router.push({ name: 'Login' });
  };

  onMounted(async () => {
  await fetchSystemInfo();
  
  // Recursive function to prevent call stacking
  const pollStats = async () => {
    await updateSystemStats();
    statsInterval = setTimeout(pollStats, 20000);
  };
  
  pollStats();
  });

  onUnmounted(() => {
    if (statsInterval) clearTimeout(statsInterval);
  });

  /**
   * Dynamic view title mapping.
   * Maps internal routes to human-readable system module names.
   */
  const pageTitle = computed(() => {
    const titles: Record<string, string> = {
      '/': 'System Overview',
      '/security': 'Vulnerabilities',
      '/sentinel': 'Network Sentinel',
      '/settings': 'Settings'
    };
    return titles[route.path] || 'K-Guard Dashboard';
  });
</script>

<template>
  <div class="min-h-screen bg-[#0b0c10] text-slate-300 font-sans flex">
    
    <Transition name="fade">
      <div v-if="isMenuOpen" 
           @click="isMenuOpen = false" 
           class="fixed inset-0 bg-black/80 z-40 lg:hidden backdrop-blur-md">
      </div>
    </Transition>

    <aside :class="[
      isMenuOpen ? 'translate-x-0' : '-translate-x-full',
      'fixed lg:sticky top-0 z-50 h-screen bg-[#0d0e12] border-r border-slate-800/60 flex flex-col shrink-0 transition-all duration-500 ease-in-out w-64 lg:translate-x-0'
    ]">
      <button @click="isMenuOpen = false" 
            class="lg:hidden absolute top-5 right-5 text-slate-400 hover:text-white p-2 transition-colors cursor-pointer">
        <span class="text-2xl font-light">✕</span>
      </button>
      
      <div class="h-14 px-6 md:px-0 md:justify-center lg:px-6 flex items-center gap-3 border-b border-slate-800/50 bg-[#111217]">
        <img src="/logo_small.png" alt="K-Guard" class="w-8 h-8 object-contain" />
        <span class="hidden lg:block text-white font-valorant text-lg tracking-[0.2em] mt-1">
          K-<span class="text-[#f05a28]">GUARD</span>
        </span>
      </div>
      
      <nav class="flex-1 flex flex-col p-4 md:p-2 lg:p-4 space-y-1 mt-2">
        <router-link to="/" @click="isMenuOpen = false" class="nav-link py-2" :class="route.path === '/' ? 'nav-active' : 'nav-inactive'">
          <span class="text-lg">📊</span>
          <div class="flex flex-col md:hidden lg:flex ml-3">
            <span class="text-[10px] font-bold uppercase tracking-widest">System Overview</span>
            <span class="text-[7px] text-slate-500 font-mono mt-0.5 uppercase">K3s Status</span>
          </div>
        </router-link>

        <router-link to="/security" @click="isMenuOpen = false" class="nav-link py-2" :class="route.path === '/security' ? 'nav-active' : 'nav-inactive'">
          <span class="text-lg">🔒</span>
          <div class="flex flex-col md:hidden lg:flex ml-3">
            <span class="text-[10px] font-bold uppercase tracking-widest">Vulnerabilities</span>
            <span class="text-[7px] text-slate-500 font-mono mt-0.5 uppercase">Trivy Scan</span>
          </div>
        </router-link>

        <router-link to="/sentinel" @click="isMenuOpen = false" class="nav-link py-2" :class="route.path === '/sentinel' ? 'nav-active' : 'nav-inactive'">
          <span class="text-lg">🌐</span>
          <div class="flex flex-col md:hidden lg:flex ml-3">
            <span class="text-[10px] font-bold uppercase tracking-widest">Network Map</span>
            <span class="text-[7px] text-slate-500 font-mono mt-0.5 uppercase">Sentinel</span>
          </div>
        </router-link>
        
        <router-link to="/settings" @click="isMenuOpen = false" class="nav-link py-2" :class="route.path === '/settings' ? 'nav-active' : 'nav-inactive'">
          <span class="text-lg">⚙️</span>
          <div class="flex flex-col md:hidden lg:flex ml-3">
            <span class="text-[10px] font-bold uppercase tracking-widest">Settings</span>
            <span class="text-[7px] text-slate-500 font-mono mt-0.5 uppercase">Infra</span>
          </div>
        </router-link>

        <div class="flex-1"></div>  
      </nav>

      <div class="hidden lg:block p-4 border-t border-slate-800/50 bg-[#0a0b0e]">
        <div class="flex items-center gap-3 mb-1">
            <p class="text-[9px] text-slate-500 uppercase tracking-widest flex items-center gap-2">
              <span class="w-1 h-1 bg-green-500 rounded-full animate-pulse"></span>
              User: <span class="text-[#f05a28] font-bold">{{ username }}</span>
            </p>
        </div>
        <div class="text-[9px] text-slate-600 font-mono break-all leading-tight uppercase"> 
          {{ systemData ? `${systemData.cluster_version} // ${systemData.vps_os}` : 'Loading...' }}
        </div>
      </div>
    </aside>

    <main class="flex-1 flex flex-col min-w-0 overflow-y-auto relative">
      <div class="absolute inset-0 pointer-events-none flex items-center justify-center z-0">
        <div class="w-[400px] h-[400px] border border-blue-500/5 rounded-full absolute"></div>
        <img src="/logo_background.png" alt="K-Guard" class="w-[350px] opacity-[0.05] pointer-events-none select-none" />
      </div>

      <header class="h-14 border-b border-slate-800/60 bg-[#111217]/80 flex items-center justify-between px-6 lg:px-8 sticky top-0 z-[45] backdrop-blur-xl">
        <div class="flex items-center gap-4">
          <button @click="isMenuOpen = !isMenuOpen" class="lg:hidden text-slate-400 hover:text-white p-2 transition-colors cursor-pointer bg-slate-800/30 rounded-sm">
            <span class="text-xl">{{ isMenuOpen ? '✕' : '☰' }}</span>
          </button>
          <h2 class="text-sm font-bold text-white tracking-widest uppercase">{{ pageTitle }}</h2>
        </div>
        
        <div class="flex items-center gap-4">
            <div class="hidden md:flex flex-col items-end">
                <span class="text-[8px] text-green-500 font-bold tracking-[0.2em] uppercase flex items-center gap-2">
                    <span class="relative flex h-1.5 w-1.5">
                        <span class="animate-ping absolute inline-flex h-full w-full rounded-full bg-green-400 opacity-75"></span>
                        <span class="relative inline-flex rounded-full h-1.5 w-1.5 bg-green-500"></span>
                    </span>
                    K3s Cloud online
                </span>
                <span class="text-[9px] text-slate-600 font-mono mt-0.5 uppercase">Latency: {{ systemLatency }}ms</span>
            </div>
            <button @click="handleLogout" class="group flex items-center gap-2 bg-red-500/10 hover:bg-red-500/20 border border-[#f05a28] px-3 py-1.5 rounded-sm transition-all duration-300 cursor-pointer">
              <span class="text-[10px] text-[#f05a28] font-bold uppercase tracking-tighter">LogOut</span>
          </button>
        </div>
      </header>

      <div class="flex-1 overflow-y-auto overflow-x-auto relative z-10 custom-scrollbar">
        <router-view v-slot="{ Component }">
            <transition name="page" mode="out-in">
              <component :is="Component" />
            </transition>
        </router-view>
      </div>
    </main>
  </div>
</template>