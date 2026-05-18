// static/aeptic_reports/monthly_reports.js

class MonthlyReportsManager {
    constructor() {
        this.currentMonth = new Date();
        this.currentMonth.setDate(1);
        this.init();
    }

    init() {
        this.setupEventListeners();
        this.loadReport(this.currentMonth);
    }

    setupEventListeners() {
        // Descargar PDF
        document.getElementById('download-pdf-btn')?.addEventListener('click', () => {
            this.downloadReport('pdf');
        });

        // Subir documento firmado (solo mes actual)
        document.getElementById('current-month-file')?.addEventListener('change', (e) => {
            this.uploadReport(e, this.currentMonth);
        });
    }

    loadReport(date) {
        const monthStr = this.dateToString(date);
        fetch(`/monthly-reports/data/?month=${monthStr}`)
            .then(r => r.json())
            .then(data => {
                if (data.status === 'success') {
                    this.populateTable(data.data);
                } else {
                    this.showError(data.message || 'Error cargando reporte');
                }
            })
            .catch(err => {
                console.error('Error:', err);
                this.showError('Error de red');
            });
    }

    downloadReport(format) {
        const monthStr = this.dateToString(this.currentMonth);
        const btn = document.getElementById('download-pdf-btn');

        if (btn) {
            const originalHTML = btn.innerHTML;  // capturar ANTES de modificar
            btn.disabled = true;
            btn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Descargando...';

            setTimeout(() => {
                window.location.href = `/monthly-reports/download/?month=${monthStr}&format=${format}`;
                btn.disabled = false;
                btn.innerHTML = originalHTML;
            }, 500);
        } else {
            // Si por algún motivo no encuentra el botón, descarga igualmente
            window.location.href = `/monthly-reports/download/?month=${monthStr}&format=${format}`;
        }
    }

    uploadReport(event, date) {
        const file = event.target.files[0];
        if (!file) return;

        const label = event.target.nextElementSibling;
        if (label) {
            label.classList.add('loading');
            label.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Subiendo...';
        }

        const formData = new FormData();
        formData.append('file', file);
        formData.append('month', this.dateToString(date));

        fetch('/monthly-reports/upload/', {
            method: 'POST',
            headers: { 'X-CSRFToken': csrftoken },
            body: formData
        })
        .then(r => r.json())
        .then(data => {
            if (label) {
                label.classList.remove('loading');
                label.innerHTML = '<i class="bi bi-cloud-upload"></i> Subir firmado';
            }
            if (data.status === 'success') {
                this.showSuccess('Documento subido correctamente');
                event.target.value = '';
            } else {
                this.showError(data.message || 'Error al subir');
            }
        })
        .catch(err => {
            if (label) {
                label.classList.remove('loading');
                label.innerHTML = '<i class="bi bi-cloud-upload"></i> Subir firmado';
            }
            console.error('Error:', err);
            this.showError('Error de red');
        });
    }

    populateTable(reportData) {
        const table = document.getElementById('report-table');
        if (!table) return;

        const thead = table.querySelector('thead');
        const tbody = table.querySelector('tbody');
        if (thead) thead.innerHTML = '';
        if (tbody) tbody.innerHTML = '';

        const headers = [
            'Fecha', 'Día Semana', 'Entrada', 'Salida', 'Ausencia',
            'Vacaciones', 'Baja', 'Festivo', 'Ordinarias', 'Extras', 'Firma'
        ];

        if (thead) {
            const headerRow = document.createElement('tr');
            headers.forEach(h => {
                const th = document.createElement('th');
                th.textContent = h;
                th.style.textAlign = 'center';
                headerRow.appendChild(th);
            });
            thead.appendChild(headerRow);
        }

        if (!reportData || reportData.length === 0) {
            if (tbody) {
                const row = document.createElement('tr');
                row.innerHTML = `<td colspan="${headers.length}" class="text-center text-muted py-4">
                    No hay datos disponibles para este mes.
                </td>`;
                tbody.appendChild(row);
            }
            return;
        }

        if (tbody) {
            reportData.forEach(dayData => {
                const row = document.createElement('tr');
                if (dayData.es_fin_semana) row.classList.add('weekend');
                row.innerHTML = `
                    <td>${dayData.fecha}</td>
                    <td>${dayData.dia_semana}</td>
                    <td>${dayData.entrada}</td>
                    <td>${dayData.salida}</td>
                    <td>${dayData.ausencia}</td>
                    <td>${dayData.vacaciones}</td>
                    <td>${dayData.baja}</td>
                    <td>${dayData.festivo}</td>
                    <td>${dayData.ordinarias}</td>
                    <td>${dayData.extras}</td>
                    <td>${dayData.firma}</td>
                `;
                tbody.appendChild(row);
            });
        }
    }

    dateToString(date) {
        const year = date.getFullYear();
        const month = String(date.getMonth() + 1).padStart(2, '0');
        return `${year}-${month}-01`;
    }

    showError(msg) {
        const statusDiv = document.getElementById('status-message');
        if (statusDiv) {
            statusDiv.className = 'alert alert-danger';
            statusDiv.textContent = msg;
            statusDiv.style.display = 'block';
            setTimeout(() => { statusDiv.style.display = 'none'; }, 5000);
        }
    }

    showSuccess(msg) {
        const statusDiv = document.getElementById('status-message');
        if (statusDiv) {
            statusDiv.className = 'alert alert-success';
            statusDiv.textContent = msg;
            statusDiv.style.display = 'block';
            setTimeout(() => { statusDiv.style.display = 'none'; }, 5000);
        }
    }
}

document.addEventListener('DOMContentLoaded', () => {
    new MonthlyReportsManager();
});