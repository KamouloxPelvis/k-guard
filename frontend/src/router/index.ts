import { createRouter, createWebHistory } from 'vue-router'
import Dashboard from '../views/Dashboard.vue'
import HealthView from '../views/HealthView.vue'
import SecurityView from '../views/SecurityView.vue'
import Settings from '../views/Settings.vue'

const routes = [
  {
    path: '/',
    component: Dashboard, 
    meta: { requiresAuth: true },
    children: [
      {
        path: '', 
        name: 'Health',
        component: HealthView,
      },
      {
        path: 'security', 
        name: 'Security',
        component: SecurityView,
      },
      {
        path: 'settings',
        name: 'Settings',
        component: Settings,
      },
    ]
  },
  {
    path: '/login',
    name: 'Login',
    component: () => import('../views/LoginView.vue')
  },
  {
    path: '/:pathMatch(.*)*',
    redirect: '/'
  }
]

const router = createRouter({
  history: createWebHistory('/'), 
  routes
})

router.beforeEach((to, _from, next) => { 
  const token = localStorage.getItem('user_token');

  if (to.meta.requiresAuth && !token) {
    next({ name: 'Login' });
  } else if (to.name === 'Login' && token) {
    next({ name: 'Health' }); 
  } else {
    next();
  }
});

export default router