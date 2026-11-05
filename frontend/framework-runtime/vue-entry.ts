import * as Vue from 'vue';

Object.assign(globalThis, { trainerRuntime: {
  modules: { vue: Vue },
  mount: (App: Vue.Component) => Vue.createApp(App).mount('#app'),
} });
