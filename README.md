# Micro-cloud -- A mini framework built on top of FastAPI

This codebase contains a mini framework built on top of FastAPI as a micro framework for faster API services development.

The primary objective is to increase the speed with which engineers can roll out API endpoints for apps, 
regardless of the side and complexity. It achieves this by abstracting away boilerplate functionality like:

- CRUD operations in a database-agnostic way — This iteration is built with MongoDB, but implementations for relational databases are similar.
- Request / Response handling (including filtering, searching, sorting, data validation and exception handling)
- Business logic abstraction

Interesting modules (files) to look at are:
- app/api/core/middleware.py
- app/api/core/queryparams.py
- app/api/core/routing.py

Others include
- app/models/* (models)
- app/routes/* (api route endpoints)
- app/schemas/* (request and response validation schemas)
- app/services/* (business logic)
