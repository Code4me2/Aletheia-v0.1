# TypeScript Architecture Design

## Overview
This document outlines the proposed TypeScript architecture that will replace the current JavaScript implementation while maintaining all functionality.

## Core Architecture Principles

### 1. Modular Design
- **Feature-based modules** instead of monolithic class
- **Dependency injection** for loose coupling
- **Service layer** for business logic
- **Clear separation of concerns**

### 2. Type Safety First
- **Strict mode** enabled
- **No implicit any**
- **Comprehensive interfaces**
- **Type guards** for runtime safety

### 3. Progressive Enhancement
- **Graceful degradation** without JS
- **Feature detection**
- **Polyfills when needed**
- **Server-side rendering ready**

## Proposed Module Structure

```
website/src/
├── core/
│   ├── App.ts                 # Main application orchestrator
│   ├── ModuleRegistry.ts      # Dynamic module loading
│   ├── StateManager.ts        # Centralized state management
│   ├── EventBus.ts           # Application-wide events
│   └── ServiceContainer.ts    # Dependency injection
├── modules/
│   ├── chat/
│   │   ├── ChatModule.ts
│   │   ├── ChatService.ts
│   │   ├── ChatView.ts
│   │   ├── components/
│   │   │   ├── MessageList.ts
│   │   │   ├── InputArea.ts
│   │   │   └── StatusBar.ts
│   │   └── types.ts
│   ├── citations/
│   │   ├── CitationModule.ts
│   │   ├── CitationService.ts
│   │   ├── CitationPanel.ts
│   │   ├── parsers/
│   │   │   ├── InlineCitationParser.ts
│   │   │   └── CitationExtractor.ts
│   │   └── types.ts
│   ├── hierarchical/
│   │   ├── HierarchicalModule.ts
│   │   ├── HierarchicalService.ts
│   │   ├── visualization/
│   │   │   ├── D3Visualization.ts
│   │   │   ├── Minimap.ts
│   │   │   └── TouchHandler.ts
│   │   ├── components/
│   │   │   ├── HistoryDrawer.ts
│   │   │   ├── Breadcrumbs.ts
│   │   │   ├── SearchDialog.ts
│   │   │   └── ContextMenu.ts
│   │   └── types.ts
│   ├── dashboard/
│   │   ├── DashboardModule.ts
│   │   ├── DashboardService.ts
│   │   ├── widgets/
│   │   │   ├── ServiceHealth.ts
│   │   │   ├── SystemInfo.ts
│   │   │   ├── LogViewer.ts
│   │   │   └── QuickActions.ts
│   │   └── types.ts
│   └── shared/
│       ├── components/
│       │   ├── Button.ts
│       │   ├── Modal.ts
│       │   └── Toast.ts
│       └── ui/
│           ├── animations.ts
│           └── themes.ts
├── services/
│   ├── api/
│   │   ├── ApiClient.ts
│   │   ├── WebhookService.ts
│   │   └── HealthCheckService.ts
│   ├── storage/
│   │   ├── StorageService.ts
│   │   ├── LocalStorage.ts
│   │   └── SessionStorage.ts
│   ├── markdown/
│   │   ├── MarkdownService.ts
│   │   ├── SecurityService.ts
│   │   └── CodeHighlighter.ts
│   └── navigation/
│       ├── Router.ts
│       ├── HistoryManager.ts
│       └── URLHashManager.ts
├── types/
│   ├── global.d.ts
│   ├── api.types.ts
│   ├── state.types.ts
│   └── vendor.d.ts
├── utils/
│   ├── dom.ts
│   ├── async.ts
│   ├── validation.ts
│   └── formatting.ts
├── config/
│   ├── app.config.ts
│   ├── api.config.ts
│   └── features.config.ts
└── main.ts                    # Application entry point
```

## Type System Design

### Core Types

```typescript
// Application-wide types
interface AppConfig {
  features: FeatureFlags;
  api: ApiConfig;
  ui: UIConfig;
}

interface AppState {
  currentSection: SectionId;
  user: UserState;
  ui: UIState;
  data: DataState;
}

interface Module {
  id: string;
  name: string;
  initialize(): Promise<void>;
  destroy(): Promise<void>;
  onShow?(): void;
  onHide?(): void;
}
```

### Feature-Specific Types

```typescript
// Citation types
interface Citation {
  id: string;
  text: string;
  source: CitationSource;
  metadata: CitationMetadata;
  position: TextPosition;
}

interface CitationSource {
  title: string;
  court?: string;
  date?: Date;
  caseNumber?: string;
  url?: string;
}

// Hierarchical types
interface HierarchyNode {
  id: string;
  level: 0 | 1 | 2 | 3;
  content: string;
  metadata: NodeMetadata;
  children: HierarchyNode[];
  parent?: string;
  position?: { x: number; y: number };
}

interface VisualizationState {
  zoom: number;
  center: Point;
  selectedNode?: string;
  highlightedPath: string[];
  searchResults: string[];
}
```

## Service Layer Architecture

### Base Service Pattern

```typescript
abstract class BaseService {
  protected eventBus: EventBus;
  protected state: StateManager;
  
  constructor(dependencies: ServiceDependencies) {
    this.eventBus = dependencies.eventBus;
    this.state = dependencies.state;
  }
  
  abstract initialize(): Promise<void>;
  abstract destroy(): void;
}
```

### Service Implementations

```typescript
class ChatService extends BaseService {
  private api: ApiClient;
  private storage: StorageService;
  private markdown: MarkdownService;
  
  async sendMessage(message: string): Promise<void> {
    // Type-safe implementation
  }
  
  async loadHistory(): Promise<ChatMessage[]> {
    // Type-safe implementation
  }
}
```

## State Management Design

### Centralized State Store

```typescript
class StateManager {
  private state: Map<string, any> = new Map();
  private subscribers: Map<string, Set<Subscriber>> = new Map();
  
  get<T>(key: StateKey): T | undefined {
    return this.state.get(key) as T;
  }
  
  set<T>(key: StateKey, value: T): void {
    const oldValue = this.state.get(key);
    this.state.set(key, value);
    this.notify(key, value, oldValue);
  }
  
  subscribe<T>(
    key: StateKey,
    callback: (value: T, oldValue?: T) => void
  ): Unsubscribe {
    // Implementation
  }
}
```

### State Slices

```typescript
interface ChatState {
  messages: ChatMessage[];
  currentChatId: string | null;
  isLoading: boolean;
  error: Error | null;
}

interface CitationState {
  citations: Map<string, Citation>;
  panelOpen: boolean;
  selectedCitation: string | null;
}
```

## Component Architecture

### Base Component Pattern

```typescript
abstract class Component<T = any> {
  protected element: HTMLElement;
  protected props: T;
  protected children: Component[] = [];
  
  constructor(props: T) {
    this.props = props;
    this.element = this.createElement();
    this.initialize();
  }
  
  abstract createElement(): HTMLElement;
  abstract render(): void;
  
  mount(parent: HTMLElement): void {
    parent.appendChild(this.element);
    this.onMount();
  }
  
  unmount(): void {
    this.onUnmount();
    this.element.remove();
  }
  
  protected onMount(): void {}
  protected onUnmount(): void {}
}
```

## Build Configuration

### Vite Configuration

```typescript
// vite.config.ts
import { defineConfig } from 'vite';
import { resolve } from 'path';

export default defineConfig({
  resolve: {
    alias: {
      '@': resolve(__dirname, './src'),
      '@modules': resolve(__dirname, './src/modules'),
      '@services': resolve(__dirname, './src/services'),
      '@types': resolve(__dirname, './src/types'),
      '@utils': resolve(__dirname, './src/utils'),
    },
  },
  build: {
    target: 'es2015',
    minify: 'terser',
    rollupOptions: {
      output: {
        manualChunks: {
          'd3': ['d3'],
          'vendor': ['marked', 'dompurify'],
        },
      },
    },
  },
});
```

### TypeScript Configuration

```json
{
  "compilerOptions": {
    "target": "ES2015",
    "module": "ESNext",
    "lib": ["ES2015", "DOM", "DOM.Iterable"],
    "strict": true,
    "esModuleInterop": true,
    "skipLibCheck": true,
    "forceConsistentCasingInFileNames": true,
    "moduleResolution": "node",
    "resolveJsonModule": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "noImplicitReturns": true,
    "noFallthroughCasesInSwitch": true,
    "baseUrl": ".",
    "paths": {
      "@/*": ["src/*"],
      "@modules/*": ["src/modules/*"],
      "@services/*": ["src/services/*"],
      "@types/*": ["src/types/*"],
      "@utils/*": ["src/utils/*"]
    }
  },
  "include": ["src/**/*"],
  "exclude": ["node_modules", "dist"]
}
```

## Migration Strategy

### Phase 1: Core Infrastructure
1. Set up build system
2. Create core services
3. Implement state management
4. Build component system

### Phase 2: Module Migration
1. Chat module (with citations)
2. Dashboard module
3. Hierarchical module

### Phase 3: Integration
1. Connect all modules
2. Migrate styles
3. Add animations
4. Performance optimization

### Phase 4: Testing & Polish
1. Unit tests
2. Integration tests
3. E2E tests
4. Performance testing

## Performance Considerations

### Code Splitting
- Lazy load large modules (D3, hierarchical viz)
- Split vendor chunks
- Preload critical resources

### Bundle Optimization
- Tree shaking
- Minification
- Compression
- CDN for large libraries

### Runtime Performance
- Virtual scrolling for large lists
- Debounced search
- Memoization for expensive operations
- Web Workers for heavy processing