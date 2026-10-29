ForgeMind feature implementation audit
Scope: Current code in backend/app, frontend/src, and the API documentation. The status measures whether each feature is wired end to end to the backend and database—not just whether a screen or endpoint exists.

1. Feature                                      status                  summary
Feature	Status	Code mapping and routes
Authentication and user accounts	            [PARTIALLY COMPLETE]	JWT token creation and validation utilities are in security.py; the token field is in SettingsPage.tsx and the API client reads it in api.ts. There is no login, registration, refresh, or user-account API or User model. The token’s configured OAuth URL, /api/v1/auth/login, has no matching route in main.py. Authentication is disabled by default in config.py.
User profile	                                [MISSING]	            /profile renders the generic placeholder in WorkspacePage.tsx. No profile model or API route exists.
Customer management / database sync	            [PARTIALLY COMPLETE]	Customer persistence is represented by customer.py; project_service.py and projects.py provide create, list, lookup by email, and delete routes. The directory is in CustomersPage.tsx. Edit/update is missing: the frontend client exposes updateCustomer, but there is no corresponding PATCH route or customer-edit UI. New customers can be created through project intake.
Project management	                            [PARTIALLY COMPLETE]	Create/list/read/delete routes live in projects.py; intake is in ProjectIntake.tsx; list, filtering, and deletion are in Dashboard.tsx. There is no project update or general status-change route. Status changes occur through workflow actions, not a general status-management control.
Project overview and status management	        [PARTIALLY COMPLETE]	The lifecycle tracker and summary are in ProjectIntelligenceViewer.tsx. Backend status transitions are tied to analysis, route review, and quoting in projects.py. The tracker is read-only: no status dropdown or general status update API exists.
Drawing file management	                        [PARTIALLY COMPLETE]	PDF upload, list, content, and delete routes are in files.py; upload/list/delete UI is in ProjectIntake.tsx and ProjectIntelligenceViewer.tsx. The file table does not show file size or a thumbnail, and uses a generic drawing/version label rather than the original filename. PDF viewing is available in the analysis review flow, rather than as a file-table preview.
Design analysis and feature inspector	        [COMPLETE]	            PDF extraction and engineering analysis are in drawing_intelligence.py and worker.py. The UI renders dimensions and review flags in DrawingAnalysisPanel.tsx, and PDF pages, zoom, callout overlays, and engineer decisions in DrawingReviewWorkspace.tsx. Analysis/review routes and persisted review state are in projects.py and project.py. Scope caveat: the supported input is PDF; extraction still requires engineering review.
Manufacturing routing	                        [COMPLETE]	            Route planning is in route_service.py and process_planner.py. The workspace supports editing operation names, sequence, machine, time, and cost, then saving route approval through ProjectIntelligenceViewer.tsx and the route-review API.
Costing and quotation	                        [PARTIALLY COMPLETE]	Persisted quotes and breakdowns are defined in quote.py and quote.py. Calculation is in costing_service.py; quote display and print-to-PDF are in ProjectIntelligenceViewer.tsx. Shop-rate and margin editing, automatic recalculation from those settings, and material/setup/overhead/profit line items are not implemented.
Dashboard and analytics	                        [PARTIALLY COMPLETE]	Chart.js charts, KPI cards, and project/activity views are in Dashboard.tsx; chart dependencies are in package.json. Data is fetched from project, drawing, analysis, and quote APIs. Some metric names and trends overstate what the data actually measures (see gaps below).
Workspace settings: API key, rates, materials	[PARTIALLY COMPLETE]	SettingsPage.tsx stores an API token in browser localStorage. Cost-template creation exists in projects.py and costing_service.py. The settings UI does not manage shop rates or default materials; there is no template list/update/delete API or UI.

2. Deep-dive gap analysis
Authentication and account management
JWT helpers exist, but that is not a complete authentication product: there is no login route, account persistence, registration, session lifecycle, or user profile. The token settings screen accepts a token supplied from elsewhere.

Authorization is also inconsistent across the API: some actions use get_current_user, while customer creation, project creation/list/read, file listing/content, and several other endpoints do not. In addition, AUTH_DISABLED_FOR_TESTING defaults to true in config.py, which bypasses token validation unless deployment configuration overrides it.

Customer management
The database-backed customer directory and create/list/delete flows exist. It is not full CRUD: there is no backend update route, despite an updateCustomer client method, and no UI to edit a customer. Intake also creates or reuses a customer by email but does not collect all fields available in the customer schema, such as address.

Project management and status
Projects can be created, listed, opened, filtered, and deleted. The status badge and lifecycle tracker display workflow progress, while analysis review, route approval, and quoting advance status through defined workflow transitions.

There is no general status-management dropdown or project update endpoint, so users cannot directly edit status or other project fields. The displayed lifecycle stages are partly a presentation mapping over backend status values; they are not independently persisted stages.

File management and analysis
Upload, list, delete, and PDF content endpoints exist. However, the file table lacks original filenames, file sizes, thumbnails, and direct preview controls. The PDF viewer is part of the analysis review interface, so file preview is not a complete standalone file-management experience. The backend file schema also does not expose a user-friendly filename or size.

The analysis flow is substantially more complete than the file table: it supports PDF extraction, turning/milling dimensions, precision fits, GD&T, bounding-box overlays, and saved engineer decisions. STEP drawings are explicitly unsupported and marked as planned.

Costing and quotation
The quote engine persists an estimate based on approved route operations and RFQ quantity. It does not implement the formula stated in COSTING_RULES.md—material, setup, overhead, and profit are not separately calculated by the quote service. Generic process routes depend on cost templates, but templates can only be created through an API; settings do not expose them for management.

process_planner.py also contains fixed operation costs for a particular socket-head screw case. That is a specialized baseline, not configurable shop-rate data. The quotation print action uses browser printing to save as PDF; the app does not generate a downloadable quotation document through a dedicated export service.

Dashboard metric accuracy
The dashboard uses backend data rather than a fixed mock dataset, but several labels do not precisely match their calculation:

“Active projects” counts all returned projects, including quoted ones.
“Drawings processed” counts uploaded drawing files, not successfully analyzed drawings.
“Avg. quoted run time” averages quote total machining minutes; that is not calendar lead time.
Monthly quote counts use the latest quote fetched per project, so multiple quotations for a project are not all counted.
The conversion trend uses current quoted status against project creation-month cohorts; it is not a historical conversion event series.
Recent activity is synthesized from current file, review, and quote records. It is not an event log, and completed analyses without a saved review are not represented as analysis-complete events.
Deletion and persistence considerations
Project deletion uses ORM cascades for related database records, but the project-delete route does not remove the corresponding physical uploaded files. Customer deletion is rejected when RFQs are linked, so customers with project history cannot currently be removed through that endpoint.

3. Stub and placeholder detection
The profile route uses the generic “module is being prepared” screen in WorkspacePage.tsx.
STEP support is explicitly described as planned in files.py and ProjectIntake.tsx.
projects.py contains the comment # ... other imports ....
FeatureMatrix.tsx displays a hardcoded complexity heuristic based on whether tolerance is standard; it is not an engineered complexity metric.
I found no static mock dashboard data arrays in the audited dashboard. The charts’ displayed values are derived from API responses, though the metric caveats above apply.

4. Prioritized roadmap
Establish production authentication and authorization: add user/account persistence, login and token lifecycle routes, a profile API/UI, disable the test bypass by default, and consistently protect API routes.
Complete project lifecycle management: add editable project fields and controlled status transitions; make the lifecycle UI reflect persisted workflow stages and rules.
Implement configurable costing: expose CRUD for cost templates/shop rates, add default-material settings, implement the documented cost formula, and recalculate estimates when rates or margins change.
Finish customer CRUD: add customer update endpoint and edit UI; reconcile the updateCustomer client method with the backend contract.
Complete file-management UX: return original filename and file size, add file previews in the files tab, clarify processing states, and ensure physical files are removed when projects are deleted.
Make dashboard analytics semantically accurate: distinguish uploaded from analyzed drawings, define “active,” add true lead-time data, and use quote/event records that support complete historical volumes and activity.
Add coverage for end-to-end paths: test authenticated workflows, customer/project CRUD, uploads and deletion, analysis and review, routing approval, quote recalculation, and dashboard metric calculations.