# Research Notes: Ledger Detail Edit & Delete Modal (CRUD)

## Decisions & Rationale

### 1. Database Schema Extension for Categories
* **Decision**: Add a `category` field (`models.CharField(max_length=100, default="미분류")`) directly to the `Ledger` model.
* **Rationale**: 
  - Having a dedicated category field at the RDBMS model level ensures full query support, enabling fast and clean indexing for monthly category-based spending statistics later.
  - Storing it within raw LLM JSONB response backup is not recommended due to indexing overhead and performance bottlenecks.
  - Defining a separate lookup master table is deferred as it introduces unnecessary schema complexity for our current MVP milestone.
* **Alternatives Considered**: 
  - *Option B (Store in JSONB)*: Rejected because indexing JSONB keys is slow and complex compared to a simple indexed column.
  - *Option C (Separate Category Table)*: Deferred to future milestones when custom categories or budget limits are implemented.

### 2. API Endpoint Layout & Routing
* **Decision**: Map individual RESTful endpoints:
  - Edit: `PATCH /api/v1/receipts/<uuid:id>/`
  - Delete: `DELETE /api/v1/receipts/<uuid:id>/`
* **Rationale**: 
  - Standardizes the API routing scheme in accordance with REST best practices.
  - Facilitates modular, clean view methods (`ReceiptDetailView` or similar) separate from the bulk retrieval list view, satisfying single-responsibility standards.
* **Alternatives Considered**:
  - *Option B (Inline in LedgerListView)*: Rejected as overloading the list view with update/delete parameters leads to complex routing logic and poor modularity.
