# DBPower AI Cloud - Admin Panel

Modern React-based administration panel for managing multi-tenant database query analysis platform.

## Features

### 🔐 Authentication & Authorization
- **JWT-based authentication** with automatic token refresh
- **Role-based access control (RBAC)** - Super Admin, Org Admin, Team Lead, User
- Protected routes with automatic redirect to login
- Secure token storage and automatic logout on 401

### 📊 Dashboard
- **Real-time statistics**: Total queries, issues, organizations, avg execution time
- **Visual analytics**: Bar charts showing query trends over time
- **Multi-tenant insights**: Organization-level metrics

### 🏢 Organization Management
- View all organizations with creation dates
- Create, update, and delete organizations (Super Admin)
- API key management with expiration tracking
- Organization-level statistics

### 🔍 Query Analysis
- **Comprehensive query list** with filtering (All, Analyzed, Unanalyzed)
- **AI-powered analysis** - Trigger analysis on slow queries
- **Detailed query view**:
  - Original SQL query
  - Anonymized version (PII protected)
  - Execution time and metadata
  - AI analysis results with severity levels
  - Issues found and recommendations

### 🎨 Modern UI
- **Responsive design** - Works on desktop, tablet, and mobile
- **Lucide icons** - Beautiful, consistent iconography
- **Interactive charts** - Recharts for data visualization
- **Intuitive navigation** - Sidebar with active route highlighting

## Tech Stack

- **React 18** - Modern React with hooks
- **TypeScript** - Type-safe development
- **Vite** - Fast build tooling and HMR
- **React Router** - Client-side routing
- **React Query (@tanstack/react-query)** - Server state management
- **Zustand** - Lightweight client state management
- **Axios** - HTTP client with interceptors
- **Recharts** - Composable charting library
- **Lucide React** - Icon system

## Architecture

```
admin-panel/
├── src/
│   ├── components/      # Reusable UI components
│   │   └── Layout.tsx   # Main layout with sidebar
│   ├── pages/           # Route pages
│   │   ├── Login.tsx    # Authentication page
│   │   ├── Dashboard.tsx # Main dashboard
│   │   ├── Organizations.tsx # Org management
│   │   └── Queries.tsx  # Query analysis
│   ├── services/        # API client
│   │   └── api.ts       # Axios instance and API functions
│   ├── store/           # State management
│   │   └── authStore.ts # Zustand auth store
│   ├── types/           # TypeScript definitions
│   │   └── index.ts     # Shared interfaces
│   ├── App.tsx          # Main app with routing
│   └── main.tsx         # Entry point
├── Dockerfile           # Multi-stage production build
├── nginx.conf           # Nginx config for SPA + API proxy
├── vite.config.ts       # Vite configuration
└── package.json         # Dependencies
```

## Development

### Prerequisites
- Node.js 18+ and npm
- API Gateway running on `http://localhost:8080`
- Backend and database services running

### Setup

1. **Install dependencies**:
```bash
cd admin-panel
npm install
```

2. **Environment variables** (optional):
Create `.env.local` file:
```env
VITE_API_BASE_URL=http://localhost:8080
```

3. **Start development server**:
```bash
npm run dev
```

The admin panel will be available at `http://localhost:3000`.

Vite dev server will proxy `/api/*` requests to the API Gateway at `http://localhost:8080`.

### Development Commands

```bash
npm run dev          # Start dev server with HMR
npm run build        # Build for production
npm run preview      # Preview production build locally
npm run lint         # Run ESLint (if configured)
```

## Production Deployment

### Docker Build

Build the Docker image:
```bash
docker build -t dbpower-admin-panel .
```

Run the container:
```bash
docker run -p 3000:80 \
  --name admin-panel \
  --network ai-analyzer-network \
  dbpower-admin-panel
```

### Docker Compose

The admin panel is included in the main `docker-compose.yml`:

```bash
# Start all services including admin panel
docker-compose up -d

# Admin panel only
docker-compose up -d admin-panel
```

Access the admin panel at `http://localhost:3000`.

### Environment Variables

In production (Docker), configure via docker-compose.yml or environment:

- **API_BASE_URL**: Not needed - nginx proxies `/api/` to `api-gateway:8000`

### Nginx Configuration

The included `nginx.conf` provides:
- **SPA routing**: All routes fallback to `index.html`
- **API proxy**: `/api/*` forwarded to API Gateway
- **Static asset caching**: 1 year cache for JS/CSS/images
- **Gzip compression**: Reduced bandwidth
- **Security headers**: XSS, clickjacking protection
- **Health check**: `/health` endpoint for monitoring

## API Integration

### Authentication Flow

1. User enters credentials on Login page
2. POST `/api/v1/auth/login` with email and password
3. Receive JWT access token
4. Store token in localStorage
5. Axios interceptor adds `Authorization: Bearer <token>` to all requests
6. On 401 response, clear token and redirect to login

### API Endpoints Used

**Authentication:**
- `POST /api/v1/auth/login` - Login with email/password
- `POST /api/v1/auth/logout` - Logout (optional)
- `GET /api/v1/auth/me` - Get current user info

**Organizations:**
- `GET /api/v1/admin/organizations` - List all organizations
- `GET /api/v1/admin/organizations/:id` - Get organization details
- `POST /api/v1/admin/organizations` - Create organization
- `PUT /api/v1/admin/organizations/:id` - Update organization
- `DELETE /api/v1/admin/organizations/:id` - Delete organization

**Teams:**
- `GET /api/v1/admin/teams?organization_id=X` - List teams
- `POST /api/v1/admin/teams` - Create team

**Users:**
- `GET /api/v1/admin/users?organization_id=X` - List users
- `POST /api/v1/admin/users` - Create user

**Queries:**
- `GET /api/v1/slow-queries` - List slow queries
- `GET /api/v1/slow-queries/:id` - Get query details
- `POST /analyzer/analyze` - Trigger AI analysis

**Statistics:**
- `GET /api/v1/stats/dashboard` - Dashboard stats
- `GET /rate-limit/info` - Rate limit info

## State Management

### Zustand Auth Store

Global authentication state:
```typescript
const { user, token, isAuthenticated, login, logout } = useAuthStore();
```

### React Query

Server state with automatic caching and refetching:
```typescript
const { data, isLoading, error } = useQuery({
  queryKey: ['queries'],
  queryFn: () => queriesAPI.list(),
});
```

Mutations for create/update/delete operations:
```typescript
const mutation = useMutation({
  mutationFn: (id) => queriesAPI.analyze(id),
  onSuccess: () => queryClient.invalidateQueries(['queries']),
});
```

## Security Features

### Client-Side
- **JWT token validation**: Automatic logout on expired/invalid tokens
- **Protected routes**: Unauthenticated users redirected to login
- **XSS prevention**: React escapes all user input by default
- **HTTPS ready**: Nginx configured for SSL/TLS termination

### Network
- **API proxy**: All API calls go through nginx, hiding backend services
- **CORS**: Handled by API Gateway
- **Rate limiting**: Enforced by API Gateway (not client-side)

### Best Practices
- Tokens stored in localStorage (consider httpOnly cookies for enhanced security)
- No sensitive data in client-side code
- API keys never exposed to frontend

## Customization

### Styling

Currently using **inline styles** for rapid development. To scale, consider:
- **CSS Modules**: Scoped styles per component
- **Tailwind CSS**: Utility-first CSS framework
- **styled-components**: CSS-in-JS with TypeScript support
- **MUI/Ant Design**: Component libraries

### Theming

To add dark mode or custom themes:
1. Create a theme context/store
2. Define color palettes
3. Replace inline styles with theme variables
4. Add theme toggle in Layout component

### Additional Features

Potential enhancements:
- **User profile page**: Update email, password, preferences
- **Team management**: Full CRUD for teams
- **Identity management**: Manage identities (client agents)
- **Audit logs**: View security and compliance logs
- **Real-time updates**: WebSocket for live query analysis
- **Export functionality**: Download queries/analysis as CSV/JSON
- **Advanced filtering**: Multi-column filtering and sorting
- **Notifications**: Toast messages for success/error states

## Troubleshooting

### Cannot connect to API Gateway

**Problem**: API requests fail with network errors.

**Solutions**:
- Ensure API Gateway is running: `docker-compose ps api-gateway`
- Check API Gateway logs: `docker-compose logs api-gateway`
- Verify proxy configuration in `vite.config.ts` (development)
- Verify nginx proxy in `nginx.conf` (production)

### Authentication loop (constant redirects to /login)

**Problem**: After login, immediately redirected back to login.

**Solutions**:
- Check browser console for token storage errors
- Verify JWT token format in localStorage
- Check API Gateway authentication middleware
- Ensure backend `/api/v1/auth/login` returns valid token

### Build fails

**Problem**: `npm run build` fails with errors.

**Solutions**:
- Clear node_modules: `rm -rf node_modules package-lock.json && npm install`
- Check for TypeScript errors: Fix type issues in components
- Verify all imports are correct

### Docker image build fails

**Problem**: `docker build` fails.

**Solutions**:
- Ensure `package.json` is in admin-panel directory
- Check Dockerfile syntax
- Verify nginx.conf exists
- Build with `--no-cache` flag: `docker build --no-cache .`

## Contributing

When adding new features:
1. Add TypeScript interfaces to `src/types/index.ts`
2. Create API functions in `src/services/api.ts`
3. Build page component in `src/pages/`
4. Add route to `src/App.tsx`
5. Update sidebar navigation in `src/components/Layout.tsx`

## License

Proprietary - DBPower AI Cloud

---

**Admin Panel Version**: 1.0.0 (Phase 6)
**Last Updated**: 2025-11-11
