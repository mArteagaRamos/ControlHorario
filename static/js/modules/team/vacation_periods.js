// ========== Vacation Periods Management ==========

let currentEditingPeriodId = null;
let vacationPeriodsModal = null;

// Inicializar cuando el DOM esté listo
document.addEventListener('DOMContentLoaded', function() {
  const modalElement = document.getElementById('addPeriodModal');
  if (modalElement) {
    vacationPeriodsModal = new bootstrap.Modal(modalElement);
  }
  loadVacationPeriods();
});

async function loadVacationPeriods() {
  try {
    const response = await fetch(window.vacationPeriodsUrls.list);
    const data = await response.json();

    if (response.ok) {
      renderVacationPeriods(data.periods);
    } else {
      showError("Error al cargar períodos: " + (data.error || 'Desconocido'));
    }
  } catch (e) {
    console.error('Error loading vacation periods:', e);
  }
}

function renderVacationPeriods(periods) {
  const container = document.getElementById('vacation-periods-container');
  const isManager = window.userRole === 'manager' || window.userRole === 'admin';

  if (!periods || periods.length === 0) {
    container.innerHTML = '<div class="text-center text-muted py-3"><small>No hay períodos especiales configurados</small></div>';
    return;
  }

  let html = `
    <div class="table-responsive">
      <table class="table table-sm table-hover mb-0">
        <thead class="table-light">
          <tr>
            <th>Nombre</th>
            <th>Configuración</th>
            <th>Unidad de Vacación</th>
            ${isManager ? '<th class="text-end">Acciones</th>' : ''}
          </tr>
        </thead>
        <tbody>
  `;

  periods.forEach(p => {
    let configText = '';
    if (p.date_from && p.date_to) {
      const dateFrom = new Date(p.date_from).toLocaleDateString('es-ES');
      const dateTo = new Date(p.date_to).toLocaleDateString('es-ES');
      configText = `<small>${dateFrom} → ${dateTo}</small>`;
    } else if (p.weekdays && p.weekdays.length > 0) {
      const dayNames = {
        'monday': 'Lunes',
        'tuesday': 'Martes',
        'wednesday': 'Miércoles',
        'thursday': 'Jueves',
        'friday': 'Viernes',
        'saturday': 'Sábado',
        'sunday': 'Domingo'
      };
      const daysStr = p.weekdays.map(d => dayNames[d]).join(', ');
      configText = `<small><i class="bi bi-repeat"></i> ${daysStr}</small>`;
    }

    const actionButtons = isManager ? `
      <td class="text-end">
        <button type="button" class="btn btn-xs btn-warning py-0 px-1"
          onclick="editPeriod('${p.id}', '${p.name}', '${p.date_from || ''}', '${p.date_to || ''}', ${p.multiplier}, ${JSON.stringify(p.weekdays || [])})"
          title="Editar">
          <i class="bi bi-pencil-square"></i>
        </button>
        <button type="button" class="btn btn-xs btn-danger py-0 px-1"
          onclick="deletePeriod('${p.id}', '${p.name}')"
          title="Eliminar">
          <i class="bi bi-trash"></i>
        </button>
      </td>
    ` : '';

    html += `
      <tr>
        <td><strong>${p.name}</strong></td>
        <td>${configText}</td>
        <td><span class="badge text-bg-info">${p.multiplier}</span></td>
        ${actionButtons}
      </tr>
    `;
  });

  html += `
        </tbody>
      </table>
    </div>
  `;

  container.innerHTML = html;
}

function openAddPeriodModal() {
  currentEditingPeriodId = null;
  document.getElementById('periodModalLabel').textContent = 'Agregar período vacacional';
  document.getElementById('period_name').value = '';
  document.getElementById('period_date_from').value = '';
  document.getElementById('period_date_to').value = '';
  document.getElementById('period_multiplier').value = '1.0';

  // Limpiar checkboxes (solo días de semana, no sábado/domingo)
  const weekdayIds = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday'];
  weekdayIds.forEach(day => {
    const checkbox = document.getElementById(`weekday_${day}`);
    if (checkbox) checkbox.checked = false;
  });

  // Mostrar primer tab (fechas)
  const dateRangeTab = document.getElementById('date-range-tab');
  if (dateRangeTab) {
    const tab = new bootstrap.Tab(dateRangeTab);
    tab.show();
  }
}

function editPeriod(id, name, dateFrom, dateTo, multiplier, weekdays) {
  currentEditingPeriodId = id;
  document.getElementById('periodModalLabel').textContent = 'Editar período vacacional';
  document.getElementById('period_name').value = name;
  document.getElementById('period_date_from').value = dateFrom;
  document.getElementById('period_date_to').value = dateTo;
  document.getElementById('period_multiplier').value = multiplier;

  // Limpiar todos los checkboxes
  const weekdayIds = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday'];
  weekdayIds.forEach(day => {
    const checkbox = document.getElementById(`weekday_${day}`);
    if (checkbox) checkbox.checked = false;
  });

  // Marcar los días de la semana correspondientes
  if (weekdays && weekdays.length > 0) {
    weekdays.forEach(day => {
      const checkbox = document.getElementById(`weekday_${day}`);
      if (checkbox) checkbox.checked = true;
    });
    // Mostrar tab de días específicos
    const weekdaysTab = document.getElementById('weekdays-tab');
    if (weekdaysTab) {
      const tab = new bootstrap.Tab(weekdaysTab);
      tab.show();
    }
  } else {
    // Mostrar tab de fechas
    const dateRangeTab = document.getElementById('date-range-tab');
    if (dateRangeTab) {
      const tab = new bootstrap.Tab(dateRangeTab);
      tab.show();
    }
  }

  vacationPeriodsModal.show();
}

document.addEventListener('DOMContentLoaded', function() {
  const savePeriodBtn = document.getElementById('savePeriodBtn');
  if (savePeriodBtn) {
    savePeriodBtn.addEventListener('click', async function() {
      const name = document.getElementById('period_name').value.trim();
      const dateFrom = document.getElementById('period_date_from').value;
      const dateTo = document.getElementById('period_date_to').value;
      const multiplier = parseFloat(document.getElementById('period_multiplier').value);

      // Obtener días de semana seleccionados
      const selectedWeekdays = Array.from(document.querySelectorAll('.weekday-checkbox:checked'))
        .map(cb => cb.value);

      // Validaciones básicas
      if (!name) {
        showError('El nombre del período es requerido');
        return;
      }

      // Al menos debe haber fechas o días de la semana
      if (!dateFrom && !dateTo && selectedWeekdays.length === 0) {
        showError('Debes configurar un rango de fechas o seleccionar días de la semana');
        return;
      }

      if ((dateFrom || dateTo) && !(dateFrom && dateTo)) {
        showError('Debes completar ambas fechas (inicio y fin)');
        return;
      }

      if (isNaN(multiplier) || multiplier < 0.1 || multiplier > 1.0) {
        showError('La unidad de vacación debe estar entre 0.1 y 1.0');
        return;
      }

      if (dateFrom && dateTo && new Date(dateFrom) > new Date(dateTo)) {
        showError('La fecha de inicio debe ser anterior a la de fin');
        return;
      }

      try {
        const url = currentEditingPeriodId
          ? window.vacationPeriodsUrls.edit
          : window.vacationPeriodsUrls.create;

        const payload = {
          name,
          date_from: dateFrom || null,
          date_to: dateTo || null,
          weekdays: selectedWeekdays.length > 0 ? selectedWeekdays : [],
          multiplier,
        };

        if (currentEditingPeriodId) {
          payload.id = currentEditingPeriodId;
        }

        const response = await fetch(url, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': window.vacationPeriodsUrls.csrf_token
          },
          body: JSON.stringify(payload)
        });

        const data = await response.json();

        if (response.ok && data.ok) {
          showSuccess(currentEditingPeriodId ? 'Período actualizado' : 'Período agregado');
          vacationPeriodsModal.hide();
          loadVacationPeriods();
        } else {
          showError('Error: ' + (data.error || 'Desconocido'));
        }
      } catch (e) {
        showError('Error de conexión: ' + e.message);
      }
    });
  }
});

function deletePeriod(id, name) {
  if (!confirm(`¿Eliminar el período "${name}"?`)) {
    return;
  }

  fetch(window.vacationPeriodsUrls.delete, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-CSRFToken': window.vacationPeriodsUrls.csrf_token
    },
    body: JSON.stringify({ id })
  })
  .then(response => response.json())
  .then(data => {
    if (data.ok) {
      showSuccess('Período eliminado');
      loadVacationPeriods();
    } else {
      showError('Error: ' + (data.error || 'Desconocido'));
    }
  })
  .catch(e => showError('Error: ' + e.message));
}

function showError(msg) {
  console.error(msg);
}

function showSuccess(msg) {
  console.log(msg);
}
