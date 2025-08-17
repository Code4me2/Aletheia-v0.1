// website/js/config.js
// Configuration will be injected from server-side based on centralized config
// This provides a fallback for development
const CONFIG = window.DATA_COMPOSE_CONFIG || {
  webhooks: {
    chat: {
      id: "c188c31c-1c45-4118-9ece-5b6057ab5177",
      url: `${window.location.protocol}//${window.location.host}/webhook/c188c31c-1c45-4118-9ece-5b6057ab5177`
    },
    hierarchicalSummarization: {
      id: "4f9e5d3c-7b2a-4e1f-9c8d-6a5b4c3d2e1f",
      url: `${window.location.protocol}//${window.location.host}/webhook/4f9e5d3c-7b2a-4e1f-9c8d-6a5b4c3d2e1f`
    }
  },
  features: {
    chat: true,
    hierarchicalSummarization: true,
    courtProcessor: true,
    haystack: true
  }
};

// Legacy support - maintain backward compatibility
CONFIG.WEBHOOK_ID = CONFIG.webhooks.chat.id;
CONFIG.WEBHOOK_URL = CONFIG.webhooks.chat.url;

// Service URLs configuration
CONFIG.services = {
  aiPortal: '/portal/',
  n8n: '/n8n',
  chat: '/chat',
  api: '/api',
  // Direct service access (for development)
  ...(window.location.hostname === 'localhost' ? {
    aiPortalDirect: `:${window.AI_PORTAL_PORT || '8102'}`,
    n8nDirect: `:${window.N8N_PORT || '8100'}`,
    haystackDirect: `http://localhost:${window.HAYSTACK_PORT || '8500'}`,
    elasticsearchDirect: `http://localhost:${window.ELASTICSEARCH_PORT || '8202'}`
  } : {})
};
