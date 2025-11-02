/**
 * Utility functions for handling API errors
 */

interface ApiError {
  error?: string;
  detail?: string | Array<{
    loc: string[];
    msg: string;
    type: string;
  }>;
  message?: string;
}

/**
 * Extract user-friendly error message from API response
 */
export const getErrorMessage = (error: unknown): string => {
  // Handle axios error
  if (error && typeof error === 'object' && 'response' in error) {
    const axiosError = error as { response?: { data?: ApiError; status?: number } };
    
    if (axiosError.response?.data) {
      const data = axiosError.response.data;
      
      // Check for validation errors (FastAPI format)
      if (Array.isArray(data.detail)) {
        const validationErrors = data.detail
          .map((err) => err.msg)
          .join(', ');
        return validationErrors || 'Validation error occurred';
      }
      
      // Check for error field
      if (data.error) {
        return data.error;
      }
      
      // Check for detail field (string)
      if (typeof data.detail === 'string') {
        return data.detail;
      }
      
      // Check for message field
      if (data.message) {
        return data.message;
      }
    }
    
    // Handle HTTP status codes
    if (axiosError.response?.status === 401) {
      return 'Invalid credentials. Please check your email and password.';
    }
    
    if (axiosError.response?.status === 403) {
      return 'Access denied. You do not have permission to perform this action.';
    }
    
    if (axiosError.response?.status === 404) {
      return 'The requested resource was not found.';
    }
    
    if (axiosError.response?.status === 500) {
      return 'Server error. Please try again later.';
    }
  }
  
  // Handle Error objects
  if (error instanceof Error) {
    return error.message;
  }
  
  // Handle string errors
  if (typeof error === 'string') {
    return error;
  }
  
  // Default error message
  return 'An unexpected error occurred. Please try again.';
};

/**
 * Format validation errors for display
 */
export const formatValidationErrors = (errors: Array<{ loc: string[]; msg: string }>): string => {
  return errors.map(err => {
    const field = err.loc[err.loc.length - 1];
    return `${field}: ${err.msg}`;
  }).join('\n');
};
