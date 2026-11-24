"""UC San Diego calendar stylesheet shared by student and client portals.

streamlit-calendar renders an iframe. CSS applied to Streamlit's main document
cannot reach FullCalendar; pass this string through its custom_css argument.
"""

UCSD_CALENDAR_CSS = r"""
:root { color-scheme: light; --ucsd-navy:#182B49; --ucsd-blue:#00629B;
        --ucsd-yellow:#FFCD00; --ucsd-line:#D7E4EF; }
html, body, #root { background:#FFFFFF !important; color:#182B49 !important; color-scheme:light !important; }
.fc, .fc-media-screen, .fc-view-harness, .fc-view, .fc-scrollgrid,
.fc-scrollgrid-section, .fc-scrollgrid-section > td,
.fc-timegrid, .fc-daygrid, .fc-list, .fc-scroller, .fc-scroller-liquid-absolute,
.fc-timegrid-body, .fc-timegrid-cols, .fc-timegrid-slots,
.fc-timegrid-col, .fc-timegrid-col-frame, .fc-daygrid-day,
.fc-daygrid-day-frame, .fc-scrollgrid-sync-table,
.fc-list-table, .fc-list-table td, .fc-list-table th {
    background-color:#FFFFFF !important; color:#182B49 !important;
}
.fc { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif !important;
      color:#182B49 !important; }
.fc .fc-toolbar { background:#FFFFFF !important; }
.fc .fc-toolbar-title { color:#182B49 !important; font-weight:700; font-size:1.4rem; }
.fc .fc-col-header-cell, .fc .fc-timegrid-axis, .fc .fc-daygrid-week-number {
    background:#EAF3FA !important; color:#182B49 !important;
}
.fc .fc-col-header-cell-cushion, .fc .fc-daygrid-day-number,
.fc .fc-timegrid-slot-label, .fc .fc-list-day-text, .fc .fc-list-day-side-text,
.fc .fc-timegrid-axis-cushion, .fc .fc-list-event-title,
.fc .fc-list-event-time, .fc .fc-timegrid-slot-label-cushion {
    color:#182B49 !important;
}
.fc-theme-standard td, .fc-theme-standard th, .fc-theme-standard .fc-scrollgrid,
.fc .fc-timegrid-slot, .fc .fc-timegrid-col, .fc .fc-daygrid-day,
.fc .fc-list-table td, .fc .fc-list-table th {
    border-color:#D7E4EF !important;
}
.fc .fc-scrollgrid { border:1px solid #D7E4EF !important; border-radius:10px; overflow:hidden; }
.fc .fc-day-today, .fc .fc-timegrid-col.fc-day-today,
.fc .fc-daygrid-day.fc-day-today, .fc .fc-daygrid-day.fc-day-today .fc-daygrid-day-frame {
    background-color:#FFF8D6 !important;
}
.fc .fc-highlight { background-color:rgba(0,98,155,.11) !important; }
.fc .fc-button-primary, .fc .fc-button {
    background:#00629B !important; color:#FFFFFF !important; border:1px solid #00629B !important;
    box-shadow:none !important; text-shadow:none !important; border-radius:6px;
    text-transform:capitalize;
}
.fc .fc-button-primary:hover, .fc .fc-button:hover {
    background:#182B49 !important; color:#FFFFFF !important; border-color:#182B49 !important;
}
.fc .fc-button-primary:not(:disabled).fc-button-active,
.fc .fc-button-primary:not(:disabled):active,
.fc .fc-button-active {
    background:#182B49 !important; border-color:#182B49 !important; color:#FFFFFF !important;
}
.fc .fc-button:disabled { opacity:.5 !important; }
.fc .fc-button:focus-visible, .fc a:focus-visible { outline:3px solid #FFCD00 !important; outline-offset:2px; }
.fc .fc-daygrid-event, .fc .fc-timegrid-event, .fc .fc-event {
    border-radius:5px; box-shadow:none !important;
}
/* Strong distinction between close-together events. Legacy workshop records
   use light cards with blue outlines; submitted events use navy with white text. */
.fc .fc-event {
    border:2px solid #00629B !important;
    border-left-width:4px !important;
    border-radius:7px !important;
    padding:2px 3px !important;
    box-shadow:0 1px 3px rgba(24,43,73,.18) !important;
    overflow:hidden;
}
.fc .fc-timegrid-event { margin:1px 2px 3px !important; }
.fc .fc-daygrid-event { margin:2px 3px !important; }
.fc .fc-event .fc-event-main, .fc .fc-event .fc-event-title,
.fc .fc-event .fc-event-time, .fc .fc-event .fc-event-main-frame,
.fc .fc-event .fc-event-title-container {
    color:#FFFFFF !important;
    -webkit-text-fill-color:#FFFFFF !important;
    font-weight:600 !important;
}
.fc .hub-event--legacy, .fc .hub-event--saved {
    background:#EAF3FA !important;
    border-color:#00629B !important;
    border-left-color:#00629B !important;
}
.fc .hub-event--legacy .fc-event-main,
.fc .hub-event--legacy .fc-event-title,
.fc .hub-event--legacy .fc-event-time,
.fc .hub-event--legacy .fc-event-main-frame,
.fc .hub-event--saved .fc-event-main,
.fc .hub-event--saved .fc-event-title,
.fc .hub-event--saved .fc-event-time,
.fc .hub-event--saved .fc-event-main-frame {
    color:#182B49 !important;
    -webkit-text-fill-color:#182B49 !important;
}
.fc .hub-event--submitted {
    background:#182B49 !important;
    border-color:#182B49 !important;
    border-left-color:#FFCD00 !important;
}
.fc .fc-timegrid-event .fc-event-title {line-height:1.3 !important;}
.fc .fc-timegrid-event .fc-event-time {font-size:.75rem !important;}
.fc .fc-timegrid-event-harness { z-index:1; }
.fc .fc-more-link {color:#00629B !important; font-weight:700 !important;}
.fc .fc-list-day-cushion {background:#EAF3FA !important;}
.fc .fc-list-event:hover td {background:#EAF3FA !important;}
.fc .fc-more-link {color:#00629B !important; font-weight:600;}
.fc .fc-popover {background:#FFFFFF !important; color:#182B49 !important; border-color:#D7E4EF !important;}
.fc .fc-popover-header {background:#EAF3FA !important; color:#182B49 !important;}
.fc .fc-non-business {background:rgba(0,98,155,.03) !important;}
"""
