# Reports Dashboard

## Data Hooks and Integration

### JS hooks
- `fetchReportData(params)` - Fetch report data based on parameters and filters
- `renderCharts(data)` - Render analytics and trend visualizations
- `renderProjectStatus(data)` - Render project status indicators and progress
- `applyFilters()` - Apply filters to report data and refresh visualization

### Planned endpoints
- `/api/reports/summary` - Summary statistics and KPIs for reports dashboard
- `/api/reports/data` - Detailed report data for analytics and charts
- `/api/reports/export` - Export report data in requested format

### Implementation notes
Export UI posts currently applied filters to `/api/reports/export` as integration-ready payload. Ready for backend API integration when endpoints become available.
