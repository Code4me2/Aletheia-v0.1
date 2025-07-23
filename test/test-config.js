// Test environment configuration
const TEST_CONFIG = {
    // Use environment variables or defaults
    services: {
        haystack: process.env.HAYSTACK_URL || 'http://localhost:8500',
        n8n: process.env.N8N_URL || 'http://localhost:8100',
        elasticsearch: process.env.ELASTICSEARCH_URL || 'http://localhost:8202',
        postgres: process.env.DATABASE_URL || 'postgresql://localhost:8200/aletheia',
        web: process.env.WEB_URL || 'http://localhost:8080',
        aiPortal: process.env.AI_PORTAL_URL || 'http://localhost:8102',
        lawyerChat: process.env.LAWYER_CHAT_URL || 'http://localhost:8101'
    },
    
    // Helper to get service URL
    getServiceUrl: function(service) {
        return this.services[service] || `http://localhost:${process.env.WEB_PORT || 8080}`;
    },
    
    // Port numbers for direct access
    ports: {
        web: process.env.WEB_PORT || 8080,
        n8n: process.env.N8N_PORT || 8100,
        lawyerChat: process.env.LAWYER_CHAT_PORT || 8101,
        aiPortal: process.env.AI_PORTAL_PORT || 8102,
        postgres: process.env.POSTGRES_PORT || 8200,
        redis: process.env.REDIS_PORT || 8201,
        elasticsearch: process.env.ELASTICSEARCH_PORT || 8202,
        haystack: process.env.HAYSTACK_PORT || 8500,
        bitnet: process.env.BITNET_PORT || 8501
    }
};

// For Node.js
if (typeof module !== 'undefined' && module.exports) {
    module.exports = TEST_CONFIG;
}

// For browser
if (typeof window !== 'undefined') {
    window.TEST_CONFIG = TEST_CONFIG;
}