<script setup lang="ts">
import { ref } from 'vue';
import { useRouter } from 'vue-router';
import api from '@/services/api'; 

const username = ref<string>('');
const password = ref<string>('');
const error = ref<string>('');
const loading = ref<boolean>(false);
const router = useRouter();

/**
 * Handles the authentication process.
 * Uses URLSearchParams to comply with FastAPI's OAuth2 Password flow.
 */

const handleLogin = async (): Promise<void> => {
    loading.value = true;
    error.value = '';

    try {
        /** * FastAPI OAuth2 expects data in application/x-www-form-urlencoded format.
         * The URLSearchParams object is converted to a string to ensure compatibility with Fetch.
         */
        const params = new URLSearchParams();
        params.append('username', username.value);
        params.append('password', password.value);

        const { data } = await api.post<{ access_token: string }>(
            '/token',    
            params.toString(), 
            {
                headers: {
                    'Content-Type': 'application/x-www-form-urlencoded'
                }
            }
        );
        
        if (data.access_token) {
            /**
             * Credentials storage for session management and API interceptor.
             * Redirection to the main dashboard follows successful authentication.
             */
            localStorage.setItem('user_token', data.access_token);
            localStorage.setItem('admin_username', username.value); 
            await router.push('/');
        }
    } catch (err: any) {
        /**
         * Error logging for debugging purposes.
         * User feedback is provided via a generic access denied message.
         */
        console.error("Login Error:", err.response?.status, err.message);
        error.value = "ACCESS DENIED: INVALID CREDENTIALS";
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
            v-model="username" 
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
}

.login-card {
  background: #1f2833;
  padding: 2.5rem;
  border-radius: 4px;
  width: 100%;
  max-width: 350px;
  text-align: center;
  box-shadow: 0 10px 30px rgba(0,0,0,0.5);
  border-top: 3px solid #f05a28;
}

</style>