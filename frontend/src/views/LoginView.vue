<script setup lang="ts">
import { ref } from 'vue';
import { useRouter } from 'vue-router';
import api from '@/services/api'; 

const pseudo = ref<string>('');
const password = ref<string>('');
const error = ref<string>('');
const loading = ref<boolean>(false);
const router = useRouter();

const handleLogin = async (): Promise<void> => {
    loading.value = true;
    error.value = '';

    try {
        // OAuth2 en FastAPI attend ce format spécifique
        const params = new URLSearchParams();
        params.append('username', pseudo.value);
        params.append('password', password.value);

        const { data } = await api.post<{ access_token: string }>(
            '/token',    
            params
        );
        
        if (data.access_token) {
            localStorage.setItem('user_token', data.access_token);
            localStorage.setItem('admin_pseudo', pseudo.value); 
            
            await router.push('/');
        }
    } catch (err: any) {
        console.error("Login Error:", err.response?.status, err.message);
        error.value = "ACCESS DENIED : INVALID CREDENTIALS";
    } finally {
        loading.value = false;
    }
};
</script>

<template>
  <div class="login-wrapper">
    <div class="login-card">
      <img src="/logo_small.png" alt="K-Guard Logo" class="logo"/>
      
      <h1 class="title font-valorant">K-GUARD</h1>
      <p class="subtitle">SYSTEM ACCESS</p>

      <form @submit.prevent="handleLogin" class="login-form">
        <div class="input-group">
          <input 
            v-model="pseudo" 
            type="text" 
            placeholder="USERNAME" 
            required 
          />
        </div>
        
        <div class="input-group">
          <input 
            v-model="password" 
            type="password" 
            placeholder="PASSWORD" 
            required 
          />
        </div>

        <button type="submit" :disabled="loading" class="login-btn">
          {{ loading ? 'INITIALIZING...' : 'CONNECT' }}
        </button>
      </form>

      <p v-if="error" class="error-msg">{{ error }}</p>
    </div>
  </div>
</template>


<style scoped>
.login-wrapper {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 100vh;
  background-color: #0b0c10;
  font-family: 'Inter', sans-serif;
}

.login-card {
  background: #1f2833;
  padding: 2.5rem;
  border-radius: 4px;
  width: 100%;
  max-width: 350px;
  text-align: center;
  box-shadow: 0 10px 30px rgba(0,0,0,0.5);
  border-top: 3px solid #f05a28; /* La touche orange K-Guard */
}

.logo {
  width: 60px;
  margin-bottom: 1rem;
}

.title {
  font-family: 'Valorant', sans-serif; /* Ta nouvelle police ! */
  color: white;
  letter-spacing: 4px;
  font-size: 1.5rem;
  margin: 0;
}

.font-valorant {
  font-family: 'Valorant', sans-serif;
  text-transform: uppercase; /* La police Valorant n'aime que les majuscules */
}

.subtitle {
  color: #66fcf1;
  font-size: 0.7rem;
  letter-spacing: 2px;
  margin-bottom: 2rem;
  opacity: 0.7;
}

.input-group {
  margin-bottom: 1rem;
}

input {
  width: 100%;
  padding: 0.8rem;
  background: #0b0c10;
  border: 1px solid #45a29e;
  border-radius: 4px;
  color: white;
  outline: none;
  transition: 0.3s;
}

input:focus {
  border-color: #f05a28;
}

.login-btn {
  width: 100%;
  padding: 0.8rem;
  background: #f05a28;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-weight: bold;
  letter-spacing: 1px;
  transition: 0.3s;
}

.login-btn:hover {
  background: #ff4b12;
  transform: translateY(-2px);
}

.error-msg {
  color: #ff4d4d;
  font-size: 0.8rem;
  margin-top: 1rem;
  font-family: monospace;
}
</style>