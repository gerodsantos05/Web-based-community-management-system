# Inventory Dashboard

## Data Hooks and API Endpoints

### Hooks exposed by inventory.js
- `fetchInventorySummary(params)` - Fetch summary statistics for inventory overview
- `fetchInventoryList(params)` - Fetch paginated list of inventory items
- `renderInventoryCharts(data)` - Render analytics/trend charts with inventory data
- `updateCharts(filters)` - Update charts based on applied filters
- `applyFilters()` - Apply client-side filtering to inventory data
- `exportInventoryCSV(filters)` - Export filtered inventory data to CSV format

### Recommended endpoints
- `/api/inventory/summary` - Summary statistics (item counts, stock status, etc.)
- `/api/inventory/list` - Paginated inventory list with filtering/sorting
- `/api/inventory/export` - Export data in requested format

### Implementation notes
Prototype uses client-side filtering/sorting/pagination with embedded JSON below. Ready for backend API integration when endpoints become available.
