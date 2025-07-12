# Component Mapping - JS to TypeScript

## Overview
This document maps current JavaScript components to their TypeScript equivalents, identifying reusable code and required refactoring.

## Code Reuse Analysis

### High Reuse Potential (80-90%)
These components can be largely reused with TypeScript wrappers:

#### 1. Configuration
- **Current**: `js/config.js`
- **Target**: `src/config/app.config.ts`
- **Changes**: Add type definitions, no logic changes

#### 2. Markdown Processing
- **Current**: Inline markdown parsing with marked.js
- **Target**: `src/services/markdown/MarkdownService.ts`
- **Changes**: Wrap in service class, add types

#### 3. API Communication
- **Current**: Fetch calls scattered throughout
- **Target**: `src/services/api/ApiClient.ts`
- **Changes**: Centralize, add response types

### Medium Reuse Potential (50-70%)
These require significant refactoring but core logic remains:

#### 1. Chat Message Handling
```javascript
// Current JS
sendMessage() {
    const input = document.getElementById('chat-input');
    const message = input.value.trim();
    // ... processing
}

// Target TS
class ChatService {
    async sendMessage(message: string): Promise<void> {
        // Reuse validation and processing logic
    }
}
```

#### 2. Citation Parsing
```javascript
// Current JS
parseCitations(text) {
    const citations = new Map();
    // Complex regex parsing
    return { html, citations };
}

// Target TS
class CitationParser {
    parse(text: string): ParseResult {
        // Reuse regex patterns and logic
    }
}
```

### Low Reuse Potential (20-40%)
These need complete restructuring:

#### 1. D3.js Visualization
- **Current**: Procedural D3 code
- **Target**: Class-based visualization with TypeScript
- **Changes**: Complete rewrite with type safety

#### 2. Event Handling
- **Current**: Direct DOM event listeners
- **Target**: Component-based event system
- **Changes**: New architecture required

## Component-by-Component Mapping

### Chat Module

#### Current Structure
```javascript
// Scattered across DataComposeApp class
- sendMessage()
- handleResponse()
- updateChatHistory()
- clearChat()
- loadChatHistory()
```

#### Target Structure
```typescript
// src/modules/chat/
├── ChatModule.ts         // Module orchestrator
├── ChatService.ts        // Business logic
├── ChatView.ts          // UI management
├── components/
│   ├── MessageList.ts   // Message display
│   ├── InputArea.ts     // User input
│   └── ModeToggle.ts    // Local/Public toggle
└── types.ts             // Type definitions
```

#### Migration Strategy
1. Extract business logic to ChatService
2. Create view components for UI
3. Maintain existing webhook integration
4. Add proper error types

### Citation System

#### Current Structure
```javascript
// Methods in DataComposeApp
- parseCitations()
- createCitationElement()
- toggleCitationPanel()
- scrollToCitation()
- highlightCitation()
```

#### Target Structure
```typescript
// src/modules/citations/
├── CitationModule.ts
├── CitationService.ts
├── parsers/
│   ├── InlineCitationParser.ts  // <cite> tags
│   └── BracketCitationParser.ts  // [X] format
├── components/
│   ├── CitationPanel.ts
│   ├── CitationEntry.ts
│   └── CitationLink.ts
└── types.ts
```

#### Key Transformations
```typescript
// Type-safe citation parsing
interface Citation {
    id: string;
    text: string;
    source: CitationSource;
    position: { start: number; end: number };
}

class InlineCitationParser {
    private readonly pattern = /<cite\s+id=["']([^"']+)["']>([^<]+)<\/cite>/g;
    
    parse(text: string): Citation[] {
        // Reuse regex logic with types
    }
}
```

### Hierarchical Visualization

#### Current Structure
```javascript
// Large procedural functions
- initializeHierarchyVisualization()
- createForceSimulation()
- handleNodeClick()
- updateVisualization()
- setupKeyboardNavigation()
```

#### Target Structure
```typescript
// src/modules/hierarchical/visualization/
├── D3Visualization.ts
├── ForceSimulation.ts
├── NodeRenderer.ts
├── LinkRenderer.ts
├── interactions/
│   ├── ClickHandler.ts
│   ├── KeyboardHandler.ts
│   └── TouchHandler.ts
└── types.ts
```

#### Complex Refactoring Required
```typescript
class D3Visualization {
    private svg: d3.Selection<SVGSVGElement>;
    private simulation: d3.Simulation<Node, Link>;
    private zoom: d3.ZoomBehavior<Element, unknown>;
    
    constructor(
        container: HTMLElement,
        private config: VisualizationConfig
    ) {
        this.initializeSvg();
        this.setupSimulation();
        this.bindEvents();
    }
}
```

### Dashboard Module

#### Current Structure
```javascript
// Dashboard-specific methods
- checkServiceHealth()
- updateServiceStatus()
- loadDocumentation()
- showLogs()
```

#### Target Structure
```typescript
// src/modules/dashboard/
├── DashboardModule.ts
├── DashboardService.ts
├── widgets/
│   ├── ServiceHealthWidget.ts
│   ├── SystemInfoWidget.ts
│   ├── LogViewerWidget.ts
│   └── QuickActionsWidget.ts
└── types.ts
```

## Shared Components Extraction

### Current Shared Functionality
```javascript
// Utility functions scattered in app.js
- debounce()
- formatTimestamp()
- copyToClipboard()
- createElement()
```

### Target Shared Components
```typescript
// src/shared/
├── components/
│   ├── Button.ts
│   ├── Modal.ts
│   ├── Toast.ts
│   └── Spinner.ts
├── utils/
│   ├── dom.ts
│   ├── async.ts
│   ├── formatting.ts
│   └── clipboard.ts
└── types/
    └── common.types.ts
```

## State Management Mapping

### Current State
```javascript
// Class properties
this.currentSection = 'chat';
this.chatHistory = new Map();
this.citations = new Map();
this.hierarchyData = null;
```

### Target State Management
```typescript
// Centralized state store
interface AppState {
    navigation: NavigationState;
    chat: ChatState;
    citations: CitationState;
    hierarchy: HierarchyState;
    dashboard: DashboardState;
}

class StateManager {
    private state = new Map<keyof AppState, any>();
    
    get<K extends keyof AppState>(key: K): AppState[K] {
        return this.state.get(key);
    }
}
```

## CSS Migration Strategy

### Current CSS
- Single 3,000+ line file
- BEM-like naming
- CSS variables for theming

### Target CSS Architecture
```typescript
// Keep existing CSS but split by module
src/modules/
├── chat/
│   └── chat.module.css
├── citations/
│   └── citations.module.css
├── hierarchical/
│   └── hierarchical.module.css
└── dashboard/
    └── dashboard.module.css

// Shared styles
src/styles/
├── variables.css    // CSS custom properties
├── base.css        // Reset and base styles
├── utilities.css   // Utility classes
└── animations.css  // Shared animations
```

## Migration Priorities

### Phase 1: Foundation (Week 1)
1. Set up TypeScript build system
2. Create type definitions
3. Implement core services
4. Port shared utilities

### Phase 2: Chat & Citations (Week 2)
1. Migrate chat module (high reuse)
2. Migrate citation system (medium reuse)
3. Test integration between modules

### Phase 3: Visualization (Week 3)
1. Rewrite D3 visualization (low reuse)
2. Port navigation features
3. Implement history management

### Phase 4: Dashboard & Polish (Week 4)
1. Migrate dashboard (medium reuse)
2. Integrate all modules
3. Performance optimization
4. Comprehensive testing

## Risk Mitigation

### High-Risk Areas
1. **D3.js Integration**: Complex visualization logic
   - Mitigation: Create abstraction layer
   
2. **State Synchronization**: Multiple state sources
   - Mitigation: Centralized state store
   
3. **Event System**: Different paradigms
   - Mitigation: Adapter pattern

### Testing Strategy
1. Unit tests for each service
2. Integration tests for module interactions
3. Visual regression tests for UI
4. Performance benchmarks

## Code Reuse Summary

| Component | Reuse % | Effort | Risk |
|-----------|---------|--------|------|
| Config | 90% | Low | Low |
| API Client | 80% | Low | Low |
| Markdown | 85% | Low | Low |
| Chat Logic | 70% | Medium | Medium |
| Citations | 60% | Medium | Medium |
| Dashboard | 50% | Medium | Medium |
| D3 Viz | 30% | High | High |
| Event System | 20% | High | Medium |

Total estimated code reuse: **55-60%** of existing logic can be preserved with TypeScript wrappers.