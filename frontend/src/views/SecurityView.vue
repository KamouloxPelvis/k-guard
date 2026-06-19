<script setup lang="ts">
  import { ref, onMounted, onUnmounted, onActivated } from 'vue';
  import api from '@/services/api'; 

  // --- INTERFACES ---
  interface AppDeployment {
    id: string;
    name: string;
    namespace: string;
    image: string;
  }

  interface Vulnerability {
    id: string;         
    package: string;   
    fixedVersion: string;
    severity: string; 
}

  interface ScanResult {
    image: string;
    status: string;
    summary?: {
      critical: number;
      high: number;
      medium: number;
      low: number;
    };
    vulnerabilities?: Vulnerability[];
  }

  // --- REACTIVE STATES ---
  const apps = ref<AppDeployment[]>([]); 
  const isLoadingApps = ref(true);
  const loadingApp = ref<string | null>(null);
  const scanResults = ref<Record<string, ScanResult>>({});
  const showVulnerabilityModal = ref(false);
  const selectedAppVulnerabilities = ref<Vulnerability[]>([]);
  const selectedAppName = ref("");
  const patchingApp = ref<string | null>(null);
  const showPatchModal = ref(false);
  const patchLogs = ref("");
  const activePatchApp = ref("");
  let logInterval: any = null;

  /**
   * Evaluates if a specific deployment is running a legacy image for testing.
   */
  const isDemoMode = (appId: string): boolean => {
    return scanResults.value[appId]?.image === 'nginx:1.18';
  };

  /**
   * Opens detailed vulnerability report for an analyzed deployment.
   */
  const openVulnerabilityDetails = (app: AppDeployment) => {
    const result = scanResults.value[app.id];
    if (result?.vulnerabilities) {
      selectedAppVulnerabilities.value = result.vulnerabilities;
      selectedAppName.value = app.name;
      showVulnerabilityModal.value = true;
    }
  };

  /**
   * Discovers all active deployments across the K3s cluster.
   */
  const fetchApps = async () => {
    try {
      const response = await api.get<AppDeployment[]>('/k3s/deployments/all');
      apps.value = response.data;
    } catch (error) {
      console.error("[K-Guard] Discovery Engine Error:", error);
    } finally {
      isLoadingApps.value = false;
    }
  };

  /**
   * Triggers a vulnerability scan for a container image.
   * Implements a polling mechanism to retrieve results once the scan is completed.
   */
  const launchScan = async (event: MouseEvent | null, appId: string, defaultImage: string) => {
    loadingApp.value = appId;
    let imageToScan = defaultImage;

    // Secret manual override for demonstration of vulnerable states
    if (event && event.shiftKey) {
      imageToScan = "nginx:1.18";
    }

    try {
      /**
       * Image scan request targeting the backend's Trivy integration.
       */
      await api.post('/scan/scan', { image: imageToScan });

      const checkInterval = setInterval(async () => {
        try {
          const { data } = await api.get<any>(`/scan/results/${encodeURIComponent(imageToScan)}`);
          
          if (data.status === 'completed') {
            const finalData: ScanResult = { ...data.data };
            if (!finalData.image) finalData.image = imageToScan;
            scanResults.value[appId] = finalData;
            
            clearInterval(checkInterval);
            loadingApp.value = null;
          } else if (data.status === 'error') {
            clearInterval(checkInterval);
            loadingApp.value = null;
            console.error("[K-Guard] Scan analysis failed for image:", imageToScan);
          }
        } catch (pollError) {
          console.error("[K-Guard] Polling service interruption:", pollError);
        }
      }, 5000); 
    } catch (error) {
      loadingApp.value = null;
    }
  };

  /**
   * Streams remediation logs from the K3s cluster during a patch operation.
   */
  const fetchPatchLogs = async (namespace: string, appName: string) => {
    try {
      const { data } = await api.get<{ logs: string }>(`/remediation/patch-logs/${namespace}/${appName}`);
      patchLogs.value = data.logs;
    } catch (e) {
      patchLogs.value += "\n[SYSTEM] Kubernetes stream connection unstable...";
    }
  };

  /**
   * Executes an automated remediation by updating the deployment image to a patched version.
   */
  const patchApplication = async (namespace: string, appName: string, appId: string) => {
    const result = scanResults.value[appId];
    const suggestion = result?.vulnerabilities?.find(v => v.fixedVersion)?.fixedVersion;
    
    if (!suggestion || !confirm(`🚀 Trigger automated remediation for ${appName}?`)) return;

    showPatchModal.value = true;
    activePatchApp.value = appName;
    patchLogs.value = "🚀 K-GUARD ENGINE: Initializing...\n🛰️ Establishing K3s cluster connection...";
    patchingApp.value = appId;

    try {
      /**
       * Deployment patch request.
       * Splits the current image string to inject the recommended version tag.
       */
      const baseImage = result.image.split(':')[0];
      await api.post('/remediation/patch-image', {
        namespace: namespace,
        deployment: appName,
        new_image: `${baseImage}:${suggestion}` 
      });

      logInterval = setInterval(() => fetchPatchLogs(namespace, appName), 2000);
    } catch (error: any) {
      patchLogs.value += `\n❌ Remediator Error: Operation failed`;
    } finally {
      patchingApp.value = null; 
    }
  };

  /**
   * Closes patch monitoring console and clears background synchronization.
   */
  const closePatchModal = () => {
    showPatchModal.value = false;
    if (logInterval) clearInterval(logInterval);
  };

  /**
   * Determines UI status indicators based on critical vulnerability metrics.
   */
  const getAppStatus = (appId: string) => {
    const result = scanResults.value[appId];
    if (!result) return { text: 'IDLE', class: 'text-slate-500 border-slate-800' };
    
    const critical = result.summary?.critical || 0;
    if (critical > 0) return { text: 'UPDATE REQUIRED', class: 'text-red-500 border-red-500/50 bg-red-500/5' };
    
    return { text: 'SECURE', class: 'text-green-500 border-green-500/50 bg-green-500/5' };
  };

  onActivated(() => {
    
  if (apps.value.length === 0) {
    fetchApps();
  }
});

  onMounted(fetchApps);
  onUnmounted(() => { if (logInterval) clearInterval(logInterval); });
  
</script>

<template>
  <div class="p-4 lg:p-6 relative z-10 font-sans">
    
    <header class="mb-4 flex justify-between items-end border-b border-slate-800/40 pb-3">
      <p class="text-[10px] text-slate-500 mt-2 uppercase tracking-[0.4em]">Vulnerability Scan & Automated Patch</p>
    </header>

    <div class="mb-4 p-2 border border-blue-500/20 bg-blue-500/5 text-[9px] text-slate-400 font-mono uppercase tracking-tighter max-w-max">
      Tip: Shift + Click for Stress Test Mode (Nginx 1.18).    
    </div>

    <Teleport to="body">
      <div v-if="showVulnerabilityModal" class="fixed inset-0 z-[100] flex items-center justify-center p-4 bg-black/90 backdrop-blur-md">
        <div class="bg-[#1c2532] border border-slate-700 w-full max-w-4xl max-h-[80vh] flex flex-col shadow-2xl">
          <div class="p-4 border-b border-slate-700 flex justify-between items-center bg-[#121822]">
            <div>
              <h2 class="text-white font-valorant text-md tracking-widest">{{ selectedAppName }}</h2>
              <p class="text-[9px] text-slate-500 uppercase mt-0.5">Security Audit Report // Trivy v0.48</p>
            </div>
            <button @click="showVulnerabilityModal = false" class="text-slate-500 hover:text-white transition-colors cursor-pointer text-xl">✕</button>
          </div>
          <div class="flex-1 overflow-y-auto p-4 bg-[#0d1117] custom-scrollbar">
            <table class="w-full text-left border-collapse font-mono">
              <thead>
                <tr class="text-[9px] text-slate-500 uppercase tracking-tighter border-b border-slate-800">
                  <th class="pb-2">ID</th>
                  <th class="pb-2">Package</th>
                  <th class="pb-2 text-green-500">Fixed</th>
                  <th class="pb-2 text-right">Severity</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-slate-800/50">
                <tr v-for="vuln in selectedAppVulnerabilities" :key="vuln.id">
                  <td class="py-2 text-[11px] text-blue-400">{{ vuln.id }}</td>
                  <td class="py-2 text-[11px] text-slate-300">{{ vuln.package }}</td>
                  <td class="py-2 text-[11px] text-green-400">{{ vuln.fixedVersion || '-' }}</td> 
                  <td class="py-2 text-right">
                    <span :class="vuln.severity === 'CRITICAL' ? 'text-red-500 bg-red-500/10 border-red-500/30' : 'text-orange-500 bg-orange-500/10 border-orange-500/30'"
                          class="text-[8px] font-bold px-1.5 py-0.5 border rounded-sm uppercase">
                      {{ vuln.severity }}
                    </span>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </Teleport>

    <Teleport to="body">
      <div v-if="showPatchModal" class="fixed inset-0 z-[110] flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm">
        <div class="bg-[#0b0f15] border border-orange-500/30 w-full max-w-3xl shadow-[0_0_50px_-12px_rgba(249,115,22,0.2)]">
          <div class="p-3 border-b border-slate-800 flex justify-between items-center bg-black/40">
            <div class="flex items-center gap-2">
              <div class="w-1.5 h-1.5 bg-orange-500 animate-pulse rounded-full"></div>
              <h2 class="text-orange-500 font-mono text-[9px] uppercase tracking-[0.2em]">Patching: {{ activePatchApp }}</h2>
            </div>
            <button @click="closePatchModal" class="text-slate-500 hover:text-white transition-colors cursor-pointer">✕</button>
          </div>
          <div class="p-4 h-64 overflow-y-auto font-mono text-[10px] bg-black/60 custom-scrollbar">
            <pre class="text-blue-400/90 whitespace-pre-wrap leading-tight">{{ patchLogs }}</pre>
          </div>
        </div>
      </div>
    </Teleport>

    <div v-if="apps.length > 0" class="grid grid-cols-1 lg:grid-cols-2 gap-4">
      <div v-for="app in apps" :key="app.id" class="relative bg-[#181b1f]/60 backdrop-blur-sm border border-slate-800 rounded-sm hover:border-blue-500/40 transition-all flex flex-col p-5">
        
        <div v-if="loadingApp === app.id" class="absolute inset-0 z-20 bg-[#0b0c10]/90 backdrop-blur-sm flex flex-col items-center justify-center">
          <div class="radar-loader mb-4 scale-75"></div>
          <p class="text-[9px] font-mono text-blue-500 animate-pulse tracking-[0.2em]">TRIVY ENGINE : SCANNING</p>
        </div>

        <div class="flex flex-col h-full">
          <div class="flex justify-between items-start mb-4">
            <div>
              <h3 class="text-sm font-bold text-slate-200 tracking-wider uppercase leading-tight">{{ app.name }}</h3>
              <div class="flex flex-col mt-0.5 gap-0.5">
                <p class="text-[9px] text-slate-400 font-mono">NS: {{ app.namespace }}</p>
                <p class="text-[10px] font-mono tracking-tight" :class="isDemoMode(app.id) ? 'text-orange-400 font-bold animate-pulse' : 'text-slate-500'">
                  {{ isDemoMode(app.id) ? '⚠️ Nginx 1.18' : app.image }}
                </p>
              </div>
            </div>
            <span :class="getAppStatus(app.id).class" class="text-[7px] font-black px-1.5 py-0.5 tracking-widest uppercase border whitespace-nowrap">
              {{ patchingApp === app.id ? 'PATCHING...' : getAppStatus(app.id).text }}
            </span>
          </div>

          <div :class="[patchingApp === app.id ? 'bg-blue-500 animate-pulse' : getAppStatus(app.id).text === 'UPDATE REQUIRED' ? 'bg-red-600' : 'bg-slate-800']" class="h-[1px] w-full mb-4"></div>

          <div class="flex-1">
            <div v-if="scanResults[app.id]" class="grid grid-cols-2 gap-px bg-slate-800/30 border border-slate-800/30 mb-4">
              <div class="bg-black/40 p-2 text-center">
                <p class="text-[7px] text-red-500 font-bold uppercase mb-0.5">Critical</p>
                <p class="text-2xl text-white font-light">{{ scanResults[app.id]?.summary?.critical ?? 0 }}</p>
              </div>
              <div class="bg-black/40 p-2 text-center">
                <p class="text-[7px] text-orange-500 font-bold uppercase mb-0.5">High</p>
                <p class="text-2xl text-white font-light">{{ scanResults[app.id]?.summary?.high ?? 0 }}</p>
              </div>
            </div>
            <div v-else class="flex items-center justify-center h-[60px] border border-dashed border-slate-800/30 mb-4 bg-black/10">
              <p class="text-[8px] text-slate-700 uppercase tracking-widest italic">Awaiting Audit</p>
            </div>
          </div>

          <div class="space-y-2 mt-auto">
            <button @click="(e) => launchScan(e, app.id, app.image)" :disabled="!!loadingApp || !!patchingApp"  
              class="w-full py-2 text-[9px] font-bold uppercase tracking-[0.2em] transition-all bg-blue-600/90 text-white hover:bg-blue-600 disabled:opacity-50 cursor-pointer">
              {{ loadingApp === app.id ? 'Scanning...' : 'Launch Scan' }}
            </button>
            <div class="flex gap-2 items-center justify-between">
              <button v-if="scanResults[app.id]" @click="openVulnerabilityDetails(app)" 
                class="flex-1 py-1.5 text-[9px] font-bold uppercase border border-slate-700 bg-slate-800/30 text-slate-400 hover:border-blue-500/50 transition-all rounded-sm cursor-pointer">
                Report
              </button>
              <button v-if="scanResults[app.id]?.summary && scanResults[app.id]!.summary!.critical > 0" 
                @click="patchApplication(app.namespace, app.name, app.id)" 
                :disabled="!!patchingApp"
                class="flex-1 py-1.5 text-[9px] font-bold uppercase border border-orange-500/40 bg-orange-500/5 text-orange-500 hover:bg-orange-600 hover:text-white transition-all rounded-sm cursor-pointer">
                Patch
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.radar-loader {
  position: relative;
  width: 50px;
  height: 50px;
  border-radius: 50%;
  border: 1px solid rgba(59, 130, 246, 0.2);
}

.radar-loader::after {
  content: "";
  position: absolute;
  top: 0; left: 0;
  width: 100%; height: 100%;
  border-radius: 50%;
  border-top: 2px solid #3b82f6;
  animation: radar-spin 2s linear infinite;
}

@keyframes radar-spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.custom-scrollbar::-webkit-scrollbar { width: 3px; }
.custom-scrollbar::-webkit-scrollbar-thumb { background: #1e293b; }
</style>