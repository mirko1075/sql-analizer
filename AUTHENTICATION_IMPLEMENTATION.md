# Authentication Implementation - Phase 7

## Overview
Complete implementation of authentication and authorization system for the frontend application with multi-tenancy support.

## Completed Features

### 1. Authentication Context (`/frontend/src/contexts/AuthContext.tsx`)
- **State Management**: Manages user authentication state, tokens, and loading status
- **Token Persistence**: Stores JWT tokens in localStorage for session persistence
- **Auto-refresh**: Automatically refreshes expired tokens on app initialization
- **Session Recovery**: Restores user session from localStorage on page reload
- **Event Handling**: Listens for 401 unauthorized events from API and auto-logs out
- **Methods**:
  - `login(email, password)`: Authenticate user and store session
  - `register(email, password, fullName)`: Register new user
  - `logout()`: Clear session and revoke tokens
  - `refreshAccessToken()`: Refresh expired access token
  - `updateUser(updates)`: Update user profile in context

### 2. Auth Hook (`/frontend/src/hooks/useAuth.ts`)
- Custom hook to access authentication context
- Type-safe access to auth state and methods
- Throws error if used outside AuthProvider

### 3. Login Page (`/frontend/src/pages/auth/Login.tsx`)
- Email and password form with validation
- Error handling with user-friendly messages
- Loading states during authentication
- Link to registration page
- Redirect to home page after successful login

### 4. Register Page (`/frontend/src/pages/auth/Register.tsx`)
- Full registration form with:
  - Full name
  - Email
  - Password (min 8 characters)
  - Password confirmation
- Client-side validation:
  - Password length check
  - Password match verification
  - Required field validation
- Error handling and loading states
- Link to login page
- Redirect to home page after successful registration

### 5. Protected Routes (`/frontend/src/components/auth/ProtectedRoute.tsx`)
- Route-level authentication guard
- Support for:
  - `requireAuth`: Require authentication (default: true)
  - `requireSuperuser`: Require superuser privileges
  - `requiredRole`: Role-based access control (prepared for future team implementation)
- Loading state while checking authentication
- Redirect to login for unauthenticated users
- Redirect authenticated users away from auth pages
- Access denied pages for insufficient permissions

### 6. Updated App Component (`/frontend/src/App.tsx`)
- Wrapped with `AuthProvider` for global auth state
- **Navigation Component**:
  - Shows user info (name, email, superuser badge)
  - Logout button
  - Conditionally shows Collectors tab only for superusers
  - Hidden when not authenticated
- **Protected Routes**:
  - Public: `/login`, `/register`
  - Protected: `/`, `/queries`, `/queries/:id`, `/stats`
  - Superuser only: `/collectors`

### 7. Service Layer Updates (`/frontend/src/services/`)
- **api.ts**: 
  - `setAuthToken()`: Set Bearer token for all requests
  - `getAuthToken()`: Retrieve current token
  - Request interceptor: Auto-add Authorization header
  - Response interceptor: Handle 401 errors and dispatch auth:unauthorized event
- **auth.service.ts**: Complete authentication API client
- **organization.service.ts**: Organization CRUD operations
- **team.service.ts**: Team management with member operations
- **database.service.ts**: Database connection management with test functionality

### 8. TypeScript Types (`/frontend/src/types/index.ts`)
- `User`: User profile with superuser flag
- `TokenResponse`: JWT token structure
- `AuthState`: Authentication state interface
- `AuthContextType`: Context API interface
- `Organization`, `Team`, `DatabaseConnection`: Multi-tenancy entities
- `UserRole`: OWNER, ADMIN, MEMBER, VIEWER
- Helper functions:
  - `hasRequiredRole(userRole, requiredRole)`: Check role hierarchy
  - `canAccessCollectors(user)`: Check collector access permission

## Authentication Flow

### Registration
1. User fills registration form
2. Frontend validates input (password length, match)
3. Call `authService.register()` with credentials
4. Backend creates user and returns JWT tokens
5. Frontend calls `/auth/me` to get user profile
6. Store tokens in localStorage and user in context
7. Set Authorization header for subsequent requests
8. Redirect to home page

### Login
1. User enters email and password
2. Call `authService.login()` with credentials
3. Backend validates and returns JWT tokens
4. Frontend fetches current user profile
5. Store tokens and user, set Authorization header
6. Redirect to home page

### Session Persistence
1. On app initialization, check localStorage for tokens
2. If found, set Authorization header
3. Verify token by calling `/auth/me`
4. If valid, restore user session
5. If invalid, try to refresh token
6. If refresh fails, clear session

### Token Refresh
1. Access token expires (detected by 401 response)
2. `auth:unauthorized` event dispatched
3. AuthContext attempts to refresh using refresh token
4. If successful, update tokens and retry request
5. If failed, logout user and redirect to login

### Logout
1. User clicks logout button
2. Call `authService.logout()` to revoke session on backend
3. Clear localStorage (tokens and user)
4. Clear Authorization header
5. Reset auth context state
6. User redirected to login page (by router)

## Security Features

### Token Management
- **Access Token**: Short-lived JWT for API requests (Bearer token)
- **Refresh Token**: Long-lived token for obtaining new access tokens
- **Secure Storage**: Tokens stored in localStorage (consider httpOnly cookies for production)
- **Auto-refresh**: Expired tokens automatically refreshed when detected

### Route Protection
- Unauthenticated users redirected to login page
- Authenticated users cannot access login/register pages
- Superuser-only routes protected with access control
- Role-based access prepared (not fully implemented yet)

### API Security
- All requests include Authorization header (except auth endpoints)
- 401 responses trigger automatic logout
- Token validation on every protected route
- Session tracking on backend

## UI/UX Features

### Loading States
- Global loading state during auth initialization
- Button loading states during form submission
- Spinner animations for better user feedback

### Error Handling
- User-friendly error messages
- Form validation with inline feedback
- Network error handling
- Backend error message display

### Responsive Design
- Mobile-friendly login/register forms
- Responsive navigation bar
- Tailwind CSS utility classes
- Consistent styling across pages

## Next Steps (Not Yet Implemented)

### 1. Organization Management UI
- Create organization form (superuser only)
- List organizations
- Edit/delete organizations
- Organization details page

### 2. Team Management UI
- Create team within organization
- List teams
- Team members management
- Role assignment (OWNER, ADMIN, MEMBER, VIEWER)
- Add/remove team members

### 3. Database Connection Management UI
- CRUD forms for database connections
- Test connection button
- Team selection (multi-tenancy)
- Encrypted credential display

### 4. Dashboard Filtering
- Filter slow queries by team
- Filter by database connection
- Multi-tenant data isolation
- Team-based statistics

### 5. Role-Based Features
- Implement team context in user state
- Complete role hierarchy checking in ProtectedRoute
- Show/hide UI elements based on role
- Team-specific navigation

### 6. User Profile Management
- Profile edit page
- Password change form
- Session management (view/revoke)
- Preferences management

### 7. Admin Panel (Superuser)
- User management
- Organization management
- System statistics
- Audit logs

## Testing

To test the authentication:

1. **Start backend**: `docker-compose up -d`
2. **Start frontend**: `cd frontend && npm run dev`
3. **Register**: Visit http://localhost:3000/register
   - Enter full name, email, password
   - Should redirect to dashboard after successful registration
4. **Logout**: Click logout button in navigation
5. **Login**: Visit http://localhost:3000/login
   - Enter email and password from registration
   - Should redirect to dashboard after successful login
6. **Protected Routes**: Try accessing `/collectors` without superuser privileges
   - Should show "Access Denied" message
7. **Session Persistence**: Refresh the page
   - Should remain logged in
8. **Token Expiry**: Wait for token to expire or manually clear access token
   - Should automatically refresh or logout

## Files Created/Modified

### Created:
- `/frontend/src/contexts/AuthContext.tsx`
- `/frontend/src/hooks/useAuth.ts`
- `/frontend/src/hooks/index.ts`
- `/frontend/src/pages/auth/Login.tsx`
- `/frontend/src/pages/auth/Register.tsx`
- `/frontend/src/pages/auth/index.ts`
- `/frontend/src/components/auth/ProtectedRoute.tsx`
- `/frontend/src/services/auth.service.ts`
- `/frontend/src/services/organization.service.ts`
- `/frontend/src/services/team.service.ts`
- `/frontend/src/services/database.service.ts`

### Modified:
- `/frontend/src/App.tsx` - Added AuthProvider and protected routes
- `/frontend/src/services/api.ts` - Added token management and interceptors
- `/frontend/src/types/index.ts` - Added auth and multi-tenancy types

## API Endpoints Used

### Authentication
- `POST /auth/register` - Register new user
- `POST /auth/login` - Login with credentials
- `POST /auth/logout` - Logout and revoke session
- `POST /auth/refresh` - Refresh access token
- `GET /auth/me` - Get current user profile

### Organizations (Prepared, not yet in UI)
- `GET /organizations` - List organizations
- `GET /organizations/{id}` - Get organization details
- `POST /organizations` - Create organization
- `PUT /organizations/{id}` - Update organization
- `DELETE /organizations/{id}` - Delete organization

### Teams (Prepared, not yet in UI)
- `GET /teams` - List teams
- `GET /teams/{id}` - Get team details
- `POST /teams` - Create team
- `PUT /teams/{id}` - Update team
- `DELETE /teams/{id}` - Delete team
- `GET /teams/{id}/members` - List team members
- `POST /teams/{id}/members` - Add team member
- `PUT /teams/{id}/members/{user_id}` - Update member role
- `DELETE /teams/{id}/members/{user_id}` - Remove team member

### Database Connections (Prepared, not yet in UI)
- `GET /database-connections` - List connections
- `GET /database-connections/{id}` - Get connection details
- `POST /database-connections` - Create connection
- `PUT /database-connections/{id}` - Update connection
- `DELETE /database-connections/{id}` - Delete connection
- `POST /database-connections/{id}/test` - Test connection

## Known Limitations

1. **Role-based Access**: ProtectedRoute has role checking prepared but not fully functional (needs team context in user state)
2. **Token Storage**: Using localStorage (consider httpOnly cookies for production)
3. **Team Context**: User object doesn't include team memberships yet (backend may need to populate this)
4. **Remember Me**: No "remember me" functionality (all sessions persistent for now)
5. **Multi-device Sessions**: No UI to view/manage active sessions yet (API exists)
6. **Password Reset**: Not implemented
7. **Email Verification**: Not implemented

## Configuration

### Environment Variables
Backend expects these variables (already configured in docker-compose.yml):
- `SECRET_KEY`: JWT signing secret
- `ACCESS_TOKEN_EXPIRE_MINUTES`: Access token lifetime (default: 30)
- `REFRESH_TOKEN_EXPIRE_DAYS`: Refresh token lifetime (default: 7)

### Frontend API URL
Update `/frontend/src/services/api.ts` if backend runs on different port:
```typescript
const api = axios.create({
  baseURL: 'http://localhost:8000/api',
  // ...
});
```
