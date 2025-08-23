# 🤖 CI/CD Fixer Agent API Documentation

**Version**: 1.0.0  
**Generated**: August 23, 2025


    🤖 **Intelligent CI/CD Failure Analysis & Fixing Platform**
    
    This API provides automated CI/CD failure analysis using advanced AI technologies:
    
    ## 🚀 **Key Features**
    
    * **Portia AI Framework**: Structured plan-based analysis workflows
    * **Google Gemini 2.5 Pro**: Advanced AI error analysis and fix generation  
    * **GitHub Integration**: Real-time webhook processing and API integration
    * **PostgreSQL Database**: Complete audit trails and analytics storage
    * **ML Analytics**: Pattern recognition, success prediction, and learning
    * **Human Approval**: Safe fix application with approval workflows
    
    ## 🔧 **Core Capabilities**
    
    * Analyze failed GitHub Actions workflows
    * Generate intelligent fix suggestions
    * Track fix effectiveness over time
    * Learn from repository-specific patterns
    * Provide comprehensive analytics and insights
    
    ## 📊 **Analytics & Learning**
    
    * Pattern recognition across repositories
    * ML-based success prediction for fixes
    * Repository-specific intelligence
    * Historical analysis and trend detection
    * Enhanced fix generation with ML insights
    
    ---
    
    **Base URL**: `http://localhost:8000` (Development) | `https://api.yourproduction.com` (Production)
    

---

## 🔗 Base URLs

- **Development**: `http://localhost:8000`
- **Production**: `https://api.yourproduction.com`

---

## 🔐 Authentication

Currently, this API does not require authentication for development. 
For production deployment, implement:

```http
Authorization: Bearer <your_jwt_token>
```

---

## 📂 Untagged

### 📖 Root

**Endpoint:**

```http
GET /
```

Root endpoint with API information.

**Responses:**

**200** - Successful Response

---

### ➕ Handle Webhook

**Endpoint:**

```http
POST /webhook
```

Handle GitHub webhook for workflow_run events.

**Responses:**

**200** - Successful Response

---

### ➕ Analyze With Portia

**Endpoint:**

```http
POST /analyze/portia
```

Analyze CI/CD failure using Portia's plan-based approach.

**Request Body:**

```json
{
  // Request body based on schema
}
```

**Responses:**

**200** - Successful Response

**422** - Validation Error

---

### 📖 Get Pending Fixes

**Endpoint:**

```http
GET /fixes
```

Get all pending fixes that require human approval.

**Responses:**

**200** - Successful Response

---

### ➕ Approve Fix

**Endpoint:**

```http
POST /fixes/{fix_id}/approve
```

Approve a suggested fix.

**Path Parameters:**

- `fix_id` *(required)* — 

**Responses:**

**200** - Successful Response

**422** - Validation Error

---

### ➕ Reject Fix

**Endpoint:**

```http
POST /fixes/{fix_id}/reject
```

Reject a suggested fix.

**Path Parameters:**

- `fix_id` *(required)* — 

**Responses:**

**200** - Successful Response

**422** - Validation Error

---

### ➕ Respond To Clarification

**Endpoint:**

```http
POST /plans/{plan_run_id}/clarifications/{clarification_id}
```

Respond to a Portia plan clarification.

**Request Body:**

```json
{
  // Request body based on schema
}
```

**Path Parameters:**

- `plan_run_id` *(required)* — 
- `clarification_id` *(required)* — 

**Responses:**

**200** - Successful Response

**422** - Validation Error

---

### 📖 Get Failure Patterns

**Endpoint:**

```http
GET /analytics/patterns
```

Get pattern analysis of workflow failures over the specified period.

**Query Parameters:**

- `days_back` *(integer, default=30)* — 

**Responses:**

**200** - Successful Response

**422** - Validation Error

---

### 📖 Get Fix Effectiveness

**Endpoint:**

```http
GET /analytics/effectiveness
```

Get statistics on fix effectiveness and approval rates.

**Responses:**

**200** - Successful Response

---

### 📖 Get Repository Profile

**Endpoint:**

```http
GET /analytics/repository/{owner}/{repo}
```

Get detailed analytics profile for a specific repository.

**Path Parameters:**

- `owner` *(required)* — 
- `repo` *(required)* — 

**Responses:**

**200** - Successful Response

**422** - Validation Error

---

### 📖 Get Analytics Dashboard

**Endpoint:**

```http
GET /analytics/dashboard
```

Get comprehensive analytics dashboard data.

**Responses:**

**200** - Successful Response

---

### ➕ Find Similar Fixes

**Endpoint:**

```http
POST /analytics/ml/similar-fixes
```

Find similar fixes using ML-based pattern recognition.

**Request Body:**

```json
{
  // Request body based on schema
}
```

**Responses:**

**200** - Successful Response

**422** - Validation Error

---

### ➕ Predict Fix Success

**Endpoint:**

```http
POST /analytics/ml/predict-success
```

Predict the success probability of a proposed fix.

**Request Body:**

```json
{
  // Request body based on schema
}
```

**Responses:**

**200** - Successful Response

**422** - Validation Error

---

### ➕ Generate Enhanced Fix

**Endpoint:**

```http
POST /analytics/ml/generate-enhanced-fix
```

Generate an enhanced fix recommendation using ML insights.

**Request Body:**

```json
{
  // Request body based on schema
}
```

**Responses:**

**200** - Successful Response

**422** - Validation Error

---

### ➕ Learn From Feedback

**Endpoint:**

```http
POST /analytics/ml/learn-from-feedback
```

Learn from user feedback to improve future recommendations.

**Request Body:**

```json
{
  // Request body based on schema
}
```

**Responses:**

**200** - Successful Response

**422** - Validation Error

---

### 📖 Get Pattern Insights

**Endpoint:**

```http
GET /analytics/ml/pattern-insights
```

Get insights from learned patterns and ML models.

**Responses:**

**200** - Successful Response

---

### 📖 Get Model Performance

**Endpoint:**

```http
GET /analytics/ml/model-performance
```

Get performance metrics of the ML models.

**Responses:**

**200** - Successful Response

---

## 📂 System

### 📖 System Health Check

**Endpoint:**

```http
GET /health
```

Check the overall health and status of all system components.

Returns the status of:
- **Database**: PostgreSQL connection status
- **GitHub API**: GitHub service availability 
- **Gemini AI**: Google Gemini API availability

This endpoint is useful for monitoring and ensuring all services are operational.

**Responses:**

**200** - System is healthy

```json
{
  "status": "healthy",
  "timestamp": "2025-08-23T10:00:00.000000",
  "services": {
    "database": "connected",
    "github_api": "available",
    "gemini_api": "available"
  }
}
```

**500** - System health check failed

---

## 📂 Analysis

### ➕ Trigger Manual Analysis

**Endpoint:**

```http
POST /analyze
```

Manually trigger CI/CD failure analysis for a specific GitHub Actions workflow run.

This endpoint allows you to analyze any workflow run by providing:
- **owner**: GitHub repository owner/organization  
- **repo**: Repository name
- **run_id**: GitHub Actions workflow run ID

The analysis will be processed asynchronously and stored in the database for later retrieval.
Use this when you want to analyze a specific failed workflow run manually.

**Request Body:**

```json
{
  // Request body based on schema
}
```

**Responses:**

**200** - Analysis triggered successfully

```json
{
  "message": "Analysis triggered successfully",
  "failure_id": "7",
  "owner": "microsoft",
  "repo": "vscode",
  "run_id": 17152193292
}
```

**400** - Invalid request parameters

**500** - Internal server error

**422** - Validation Error

---

## 📊 OpenAPI Schema

Developers can access the **machine-readable schema**:

```
GET /openapi.json
```

This schema can be imported into **Postman, Insomnia, Swagger Editor, or GitHub Copilot** for autocompletion and testing.

## 📖 Interactive Documentation

- **Swagger UI**: `GET /docs` - Interactive API testing interface
- **ReDoc**: `GET /redoc` - Clean documentation interface

## ⚠️ Error Format

All error responses follow this format:

```json
{
  "detail": "Error message describing what went wrong"
}
```

Common HTTP status codes:
- `200` - Success
- `400` - Bad Request (invalid parameters)
- `401` - Unauthorized (authentication required)  
- `404` - Not Found (resource doesn't exist)
- `422` - Validation Error (invalid request body)
- `500` - Internal Server Error

---

**Generated automatically from OpenAPI schema** ✨
