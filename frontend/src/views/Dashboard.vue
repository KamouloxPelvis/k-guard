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
  const username = ref<string>(localStorage.getItem('admin_username') || 'Admin');
  const isMenuOpen = ref(false);
  const route = useRoute();
  const router = useRouter();
  let statsInterval: any = null;

  /**
   * Latency calculation and health check heartbeat.
   * Pings the /health endpoint to monitor backend availability and response time.
   */
  const updateSystemStats = async () => {
    const start = Date.now();
    try {
      const response = await api.get('/health');
      if (response.status === 200) {
        systemLatency.value = Date.now() - start;
      }
    } catch (e) {
      systemLatency.value = 0;
      console.warn("[K-Guard] Server heartbeat lost");
    }
  };

  /**
   * Fetches core cluster information (K3s version, OS, Uptime).
   */
  const fetchSystemInfo = async () => {
    try {
      const { data } = await api.get('/k3s/status');
      systemData.value = data;
    } catch (error) {
      console.error("Dashboard: Cluster Status Error", error);
    }
  };

  /**
   * Handles user logout by clearing local credentials and redirecting to Login.
   */
  const handleLogout = () => {
    localStorage.removeItem('user_token');
    localStorage.removeItem('admin_username'); 
    router.push({ name: 'Login' });
  };

  onMounted(async () => {
    // Initial data synchronization
    await fetchSystemInfo();
    await updateSystemStats();
    
    // Auto-refresh latency and heartbeat status every 20 seconds
    statsInterval = setInterval(updateSystemStats, 20000);
  });

  onUnmounted(() => {
    // Cleanup interval to prevent memory leaks in the browser
    if (statsInterval) clearInterval(statsInterval);
  });

  /**
   * Computed page title based on the active router path.
   */
  const pageTitle = computed(() => {
    if (route.path === '/') return 'System Overview';
    if (route.path === '/security') return 'Vulnerabilities';
    if (route.path === '/sentinel') return 'Network Sentinel';
    if (route.path === '/settings') return 'Settings';
    return 'K-Guard Dashboard';
  });
</script>

<template>
  <div class="min-h-screen bg-[#0b0c10] text-slate-300 font-sans flex overflow-auto">
    
    <Transition name="fade">
      <div v-if="isMenuOpen" 
           @click="isMenuOpen = false" 
           class="fixed inset-0 bg-black/80 z-40 lg:hidden backdrop-blur-md">
      </div>
    </Transition>

    <aside :class="[
      isMenuOpen ? 'translate-x-0' : '-translate-x-full',
      'fixed lg:relative z-50 h-full bg-[#0d0e12] border-r border-slate-800/60 flex flex-col shrink-0 transition-all duration-500 ease-in-out w-72 lg:translate-x-0 md:w-20 lg:w-72'
    ]">
      <button @click="isMenuOpen = false" 
            class="lg:hidden absolute top-5 right-5 text-slate-400 hover:text-white p-2 transition-colors cursor-pointer">
        <span class="text-2xl font-light">✕</span>
      </button>
      
      <div class="h-20 px-6 md:px-0 md:justify-center lg:px-8 flex items-center gap-4 border-b border-slate-800/50 bg-[#111217]">
        <img src="/logo_small.png" alt="K-Guard" class="w-10 h-10 object-contain" />
        <span class="hidden lg:block text-white font-valorant text-xl tracking-[0.2em] mt-1">
          K-<span class="text-[#f05a28]">GUARD</span>
        </span>
      </div>
      
      <nav class="flex-1 p-4 md:p-3 lg:p-6 space-y-4 mt-4">
        <router-link to="/" @click="isMenuOpen = false" class="nav-link" :class="route.path === '/' ? 'nav-active' : 'nav-inactive'">
          <span class="text-xl">📊</span>
          <div class="flex flex-col md:hidden lg:flex">
            <span class="text-[11px] font-bold uppercase tracking-widest">System Overview</span>
            <span class="text-[8px] text-slate-500 font-mono mt-0.5 uppercase">K3s Cluster Status</span>
          </div>
        </router-link>

        <router-link to="/security" @click="isMenuOpen = false" class="nav-link" :class="route.path === '/security' ? 'nav-active' : 'nav-inactive'">
          <span class="text-xl">🔒</span>
          <div class="flex flex-col md:hidden lg:flex">
            <span class="text-[11px] font-bold uppercase tracking-widest">Vulnerabilities</span>
            <span class="text-[8px] text-slate-500 font-mono mt-0.5 uppercase">Trivy Image Scan</span>
          </div>
        </router-link>

        <router-link to="/sentinel" @click="isMenuOpen = false" class="nav-link" :class="route.path === '/sentinel' ? 'nav-active' : 'nav-inactive'">
          <span class="text-xl">🌐</span>
          <div class="flex flex-col md:hidden lg:flex">
            <span class="text-[11px] font-bold uppercase tracking-widest">Network Map</span>
            <span class="text-[8px] text-slate-500 font-mono mt-0.5 uppercase">Network Sentinel</span>
          </div>
        </router-link>
        
        <router-link to="/settings" @click="isMenuOpen = false" class="nav-link" :class="route.path === '/settings' ? 'nav-active' : 'nav-inactive'">
          <span class="text-xl">⚙️</span>
          <div class="flex flex-col md:hidden lg:flex">
            <span class="text-[11px] font-bold uppercase tracking-widest">Settings</span>
            <span class="text-[8px] text-slate-500 font-mono mt-0.5 uppercase">Infra & Debug</span>
          </div>
        </router-link>
      </nav>

      <div class="hidden lg:block p-6 border-t border-slate-800/50 bg-[#0a0b0e]">
        <div class="flex items-center gap-3 mb-3">
            <p class="text-[10px] text-slate-500 uppercase tracking-widest flex items-center gap-2">
              <span class="w-1.5 h-1.5 bg-green-500 rounded-full animate-pulse"></span>
              Authenticated as 
              <span class="text-[#f05a28] font-bold">{{ username }}</span>
            </p>
        </div>
        <div class="text-[10px] text-slate-600 font-mono break-all leading-tight uppercase"> 
          Kubernetes & OS Distribution versions : <br />
          {{ systemData ? `${systemData.cluster_version} // ${systemData.vps_os}` : 'Loading system info...' }}
        </div>
      </div>
    </aside>

    <main class="flex-1 flex flex-col min-w-0 relative">
      <div class="absolute inset-0 pointer-events-none flex items-center justify-center z-0">
        <div class="w-[500px] h-[500px] border border-blue-500/5 rounded-full absolute"></div>
        <img src="/logo_background.png" alt="K-Guard" class="w-[450px] opacity-[0.05] pointer-events-none select-none" />
      </div>

      <header class="h-20 border-b border-slate-800/60 bg-[#111217]/80 flex items-center justify-between px-6 lg:px-10 sticky top-0 z-[45] backdrop-blur-xl">
        <div class="flex items-center gap-6">
          <button @click="isMenuOpen = !isMenuOpen" class="lg:hidden text-slate-400 hover:text-white p-2 transition-colors cursor-pointer bg-slate-800/30 rounded-sm">
            <span class="text-xl">{{ isMenuOpen ? '✕' : '☰' }}</span>
          </button>
          
          <h2 class="text-xl font-extralight text-white tracking-tight uppercase">{{ pageTitle }}</h2>
        </div>
        
        <div class="flex items-center gap-6">
            <div class="hidden md:flex flex-col items-end">
                <span class="text-[9px] text-green-500 font-bold tracking-[0.2em] uppercase flex items-center gap-2">
                    <span class="relative flex h-2 w-2">
                        <span class="animate-ping absolute inline-flex h-full w-full rounded-full bg-green-400 opacity-75"></span>
                        <span class="relative inline-flex rounded-full h-2 w-2 bg-green-500"></span>
                    </span>
                    K3s Cloud online
                </span>
                <span class="text-[10px] text-slate-600 font-mono mt-1 uppercase">Latency: {{ systemLatency }}ms</span>
            </div>
            <button @click="handleLogout" class="group flex items-center gap-2 bg-red-500/10 hover:bg-red-500/20 border border-[#f05a28] px-4 py-2 rounded-sm transition-all duration-300 cursor-pointer">
              <span class="text-xs text-[#f05a28] font-bold uppercase tracking-tighter">LogOut</span>
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