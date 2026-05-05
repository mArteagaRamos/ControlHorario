# users/tests/test_auth.py
#
# Bloque 3: Tests de Autenticación
# Cubre: login, logout, set_password, selección de empresa, flujo auditor
# Ejecutar: python manage.py test users.tests.test_auth

import uuid
from django.urls import reverse
from django.contrib.auth import SESSION_KEY

from audit.models import AuditLog
from users.models import Users, UserCompany
from users.tests.conftest import BaseTestCase, make_user, make_company, make_membership


# ─────────────────────────────────────────────────────────────────────────────
# BLOQUE 3.1 — Login Happy Path
# ─────────────────────────────────────────────────────────────────────────────

class LoginHappyPathTest(BaseTestCase):

    def _post_login(self, email, password):
        return self.client.post(
            reverse('login'),
            {'username': email, 'password': password, 'step': 'credentials'},
        )

    def test_valid_credentials_log_user_in(self):
        """Login con credenciales válidas autentica al usuario."""
        response = self._post_login('employee@test.com', self.DEFAULT_PASSWORD)
        self.assertIn(SESSION_KEY, self.client.session)

    def test_single_company_redirects_to_home_timetracking(self):
        """Usuario con una sola empresa redirige a home_timetracking."""
        response = self._post_login('employee@test.com', self.DEFAULT_PASSWORD)
        self.assertRedirects(
            response, reverse('home_timetracking'), fetch_redirect_response=False
        )

    def test_single_company_sets_company_id_in_session(self):
        """Login con una empresa guarda company_id en sesión."""
        self._post_login('employee@test.com', self.DEFAULT_PASSWORD)
        self.assertIn('company_id', self.client.session)
        self.assertEqual(
            self.client.session['company_id'],
            str(self.company1.id),
        )

    def test_multiple_companies_shows_company_selector(self):
        """Usuario con 2+ empresas ve el selector de empresa."""
        make_membership(self.employee_user, self.company2)
        response = self._post_login('employee@test.com', self.DEFAULT_PASSWORD)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['show_company_selector'])

    def test_multiple_companies_sets_pending_company_selection(self):
        """Con 2+ empresas, se marca pending_company_selection en sesión."""
        make_membership(self.employee_user, self.company2)
        self._post_login('employee@test.com', self.DEFAULT_PASSWORD)
        self.assertTrue(self.client.session.get('pending_company_selection'))

    def test_successful_login_creates_audit_log(self):
        """Login exitoso crea un AuditLog con reason='Login exitoso'."""
        self._post_login('employee@test.com', self.DEFAULT_PASSWORD)
        exists = AuditLog.objects.filter(
            user=self.employee_user,
            reason='Login exitoso',
        ).exists()
        self.assertTrue(exists)

    def test_nav_history_cleared_on_login(self):
        """El historial de navegación se limpia al hacer login."""
        session = self.client.session
        session['nav_history'] = [{'name': 'old_page', 'path': '/old/'}]
        session.save()
        self._post_login('employee@test.com', self.DEFAULT_PASSWORD)
        self.assertEqual(self.client.session.get('nav_history'), [])


# ─────────────────────────────────────────────────────────────────────────────
# BLOQUE 3.2 — Login Edge Cases
# ─────────────────────────────────────────────────────────────────────────────

class LoginEdgeCasesTest(BaseTestCase):

    def _post_login(self, email, password):
        return self.client.post(
            reverse('login'),
            {'username': email, 'password': password, 'step': 'credentials'},
        )

    def test_wrong_password_shows_error(self):
        """Contraseña incorrecta muestra mensaje de error."""
        response = self._post_login('employee@test.com', 'WrongPass999!')
        self.assertEqual(response.status_code, 200)
        msgs = [str(m) for m in response.context['messages']]
        self.assertIn('Email o contraseña incorrectos.', msgs)

    def test_nonexistent_email_shows_error(self):
        """Email que no existe muestra mensaje de error."""
        response = self._post_login('noexiste@test.com', self.DEFAULT_PASSWORD)
        self.assertEqual(response.status_code, 200)
        msgs = [str(m) for m in response.context['messages']]
        self.assertIn('Email o contraseña incorrectos.', msgs)

    def test_wrong_credentials_creates_audit_log(self):
        """Login fallido crea AuditLog con reason que contiene 'fallido'."""
        self._post_login('noexiste@test.com', self.DEFAULT_PASSWORD)
        exists = AuditLog.objects.filter(
            reason__icontains='fallido',
        ).exists()
        self.assertTrue(exists)

    def test_suspended_user_cannot_login(self):
        """Usuario suspendido no puede hacer login y ve mensaje de error."""
        suspended = make_user(
            email='suspended@test.com',
            dni='SUSP001',
            status=Users.StatusChoices.SUSPENDED,
            password=self.DEFAULT_PASSWORD,
        )
        response = self._post_login('suspended@test.com', self.DEFAULT_PASSWORD)
        self.assertEqual(response.status_code, 200)
        msgs = [str(m) for m in response.context['messages']]
        self.assertIn(
            'Tu cuenta ha sido suspendida. Puede ponerse en contacto a través de info@aeptic.es.',
            msgs,
        )

    def test_suspended_user_login_creates_audit_log(self):
        """Login de usuario suspendido crea AuditLog con reason adecuado."""
        suspended = make_user(
            email='suspended2@test.com',
            dni='SUSP002',
            status=Users.StatusChoices.SUSPENDED,
            password=self.DEFAULT_PASSWORD,
        )
        self._post_login('suspended2@test.com', self.DEFAULT_PASSWORD)
        exists = AuditLog.objects.filter(
            reason='Intento de login: cuenta suspendida',
        ).exists()
        self.assertTrue(exists)

    def test_deleted_user_cannot_login(self):
        """Usuario con deleted_at != null no puede hacer login."""
        from django.utils import timezone
        deleted = make_user(
            email='deleted@test.com',
            dni='DEL001',
            password=self.DEFAULT_PASSWORD,
        )
        deleted.deleted_at = timezone.now()
        deleted.save(update_fields=['deleted_at'])

        response = self._post_login('deleted@test.com', self.DEFAULT_PASSWORD)
        self.assertEqual(response.status_code, 200)
        msgs = [str(m) for m in response.context['messages']]
        self.assertTrue(
            any('incorrectos' in m or 'eliminada' in m for m in msgs)
        )

    def test_user_without_active_memberships_cannot_login(self):
        """Usuario sin membresías activas no puede completar el login."""
        user = make_user(
            email='nomember@test.com',
            dni='NOMEM01',
            password=self.DEFAULT_PASSWORD,
            must_change_password=False,
        )
        response = self._post_login('nomember@test.com', self.DEFAULT_PASSWORD)
        self.assertEqual(response.status_code, 200)
        msgs = [str(m) for m in response.context['messages']]
        self.assertIn(
            'No tienes ninguna membresía activa. Puede ponerse en contacto a través de info@aeptic.es.',
            msgs,
        )

    def test_user_with_only_deleted_membership_cannot_login(self):
        """Usuario cuya única membresía está soft-deleted no puede completar login."""
        from django.utils import timezone
        user = make_user(
            email='deletedmember@test.com',
            dni='DMEM001',
            password=self.DEFAULT_PASSWORD,
            must_change_password=False,
        )
        membership = make_membership(user, self.company1)
        membership.deleted_at = timezone.now()
        membership.save(update_fields=['deleted_at'])

        response = self._post_login('deletedmember@test.com', self.DEFAULT_PASSWORD)
        msgs = [str(m) for m in response.context['messages']]
        self.assertIn(
            'No tienes ninguna membresía activa. Puede ponerse en contacto a través de info@aeptic.es.',
            msgs,
        )

    def test_invalid_form_creates_audit_log(self):
        """Formulario inválido (sin email) crea AuditLog de validación fallida."""
        self.client.post(
            reverse('login'),
            {'username': '', 'password': '', 'step': 'credentials'},
        )
        exists = AuditLog.objects.filter(
            reason__icontains='validación',
        ).exists()
        self.assertTrue(exists)


# ─────────────────────────────────────────────────────────────────────────────
# BLOQUE 3.3 — SetPassword Flow
# ─────────────────────────────────────────────────────────────────────────────

class SetPasswordFlowTest(BaseTestCase):

    def setUp(self):
        super().setUp()
        self.new_user = make_user(
            email='newuser@test.com',
            dni='NEW001',
            password=self.DEFAULT_PASSWORD,
            must_change_password=True,
        )
        make_membership(self.new_user, self.company1)

    def _post_login(self, email, password):
        return self.client.post(
            reverse('login'),
            {'username': email, 'password': password, 'step': 'credentials'},
        )

    def _post_set_password(self, new_password, confirm_password):
        return self.client.post(
            reverse('login'),
            {
                'step': 'set_password',
                'new_password': new_password,
                'confirm_password': confirm_password,
            },
        )

    def test_must_change_password_shows_set_password_form(self):
        """Usuario con must_change_password=True ve el formulario de cambio."""
        response = self._post_login('newuser@test.com', self.DEFAULT_PASSWORD)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['show_set_password'])

    def test_valid_new_password_completes_login(self):
        """Contraseña válida completa el login y redirige."""
        self._post_login('newuser@test.com', self.DEFAULT_PASSWORD)
        response = self._post_set_password('NewPass123!', 'NewPass123!')
        self.assertRedirects(
            response, reverse('home_timetracking'), fetch_redirect_response=False
        )

    def test_valid_new_password_sets_must_change_password_false(self):
        """Después de cambiar contraseña, must_change_password=False."""
        self._post_login('newuser@test.com', self.DEFAULT_PASSWORD)
        self._post_set_password('NewPass123!', 'NewPass123!')
        self.new_user.refresh_from_db()
        self.assertFalse(self.new_user.must_change_password)

    def test_password_too_short_shows_error(self):
        """Contraseña menor de 8 caracteres muestra error."""
        self._post_login('newuser@test.com', self.DEFAULT_PASSWORD)
        response = self._post_set_password('Sh0rt!', 'Sh0rt!')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['show_set_password'])
        form = response.context['set_password_form']
        self.assertFalse(form.is_valid())

    def test_password_without_uppercase_shows_error(self):
        """Contraseña sin mayúscula muestra error de validación."""
        self._post_login('newuser@test.com', self.DEFAULT_PASSWORD)
        response = self._post_set_password('nouppercase1!', 'nouppercase1!')
        form = response.context['set_password_form']
        self.assertIn('new_password', form.errors)

    def test_password_without_lowercase_shows_error(self):
        """Contraseña sin minúscula muestra error de validación."""
        self._post_login('newuser@test.com', self.DEFAULT_PASSWORD)
        response = self._post_set_password('NOLOWER123!', 'NOLOWER123!')
        form = response.context['set_password_form']
        self.assertIn('new_password', form.errors)

    def test_password_without_digit_shows_error(self):
        """Contraseña sin dígito muestra error de validación."""
        self._post_login('newuser@test.com', self.DEFAULT_PASSWORD)
        response = self._post_set_password('NoDigitPass!', 'NoDigitPass!')
        form = response.context['set_password_form']
        self.assertIn('new_password', form.errors)

    def test_password_without_special_char_shows_error(self):
        """Contraseña sin carácter especial muestra error de validación."""
        self._post_login('newuser@test.com', self.DEFAULT_PASSWORD)
        response = self._post_set_password('NoSpecial123', 'NoSpecial123')
        form = response.context['set_password_form']
        self.assertIn('new_password', form.errors)

    def test_passwords_dont_match_shows_error(self):
        """Contraseñas que no coinciden muestran error en confirm_password."""
        self._post_login('newuser@test.com', self.DEFAULT_PASSWORD)
        response = self._post_set_password('NewPass123!', 'Different123!')
        form = response.context['set_password_form']
        self.assertIn('confirm_password', form.errors)

    def test_unauthenticated_set_password_redirects_to_login(self):
        """POST a set_password sin estar autenticado redirige a login."""
        response = self._post_set_password('NewPass123!', 'NewPass123!')
        self.assertRedirects(
            response, reverse('login'), fetch_redirect_response=False
        )


# ─────────────────────────────────────────────────────────────────────────────
# BLOQUE 3.4 — Company Selection
# ─────────────────────────────────────────────────────────────────────────────

class CompanySelectionTest(BaseTestCase):

    def setUp(self):
        super().setUp()
        make_membership(self.employee_user, self.company2)

    def _post_login(self, email, password):
        return self.client.post(
            reverse('login'),
            {'username': email, 'password': password, 'step': 'credentials'},
        )

    def _post_select_company(self, company_id):
        return self.client.post(
            reverse('login'),
            {'step': 'select_company', 'company_id': str(company_id)},
        )

    def test_selecting_valid_company_redirects_to_home(self):
        """Seleccionar empresa válida redirige a home_timetracking."""
        self._post_login('employee@test.com', self.DEFAULT_PASSWORD)
        response = self._post_select_company(self.company1.id)
        self.assertRedirects(
            response, reverse('home_timetracking'), fetch_redirect_response=False
        )

    def test_selecting_company_sets_company_id_in_session(self):
        """Seleccionar empresa guarda company_id correcto en sesión."""
        self._post_login('employee@test.com', self.DEFAULT_PASSWORD)
        self._post_select_company(self.company2.id)
        self.assertEqual(
            self.client.session['company_id'],
            str(self.company2.id),
        )

    def test_selecting_company_clears_pending_company_selection(self):
        """Seleccionar empresa elimina pending_company_selection de sesión."""
        self._post_login('employee@test.com', self.DEFAULT_PASSWORD)
        self._post_select_company(self.company1.id)
        self.assertNotIn('pending_company_selection', self.client.session)

    def test_unauthenticated_select_company_redirects_to_login(self):
        """POST a select_company sin autenticar redirige a login."""
        response = self._post_select_company(self.company1.id)
        self.assertRedirects(
            response, reverse('login'), fetch_redirect_response=False
        )


# ─────────────────────────────────────────────────────────────────────────────
# BLOQUE 3.5 — Auditor Login
# ─────────────────────────────────────────────────────────────────────────────

class AuditorLoginTest(BaseTestCase):

    def _post_login(self, email, password):
        return self.client.post(
            reverse('login'),
            {'username': email, 'password': password, 'step': 'credentials'},
        )

    def test_auditor_login_creates_audit_log(self):
        """Login de auditor crea AuditLog con reason='Login exitoso (Auditor)'."""
        self._post_login('auditor@test.com', self.DEFAULT_PASSWORD)
        exists = AuditLog.objects.filter(
            user=self.auditor_user,
            reason='Login exitoso (Auditor)',
        ).exists()
        self.assertTrue(exists)

    def test_auditor_with_must_change_password_shows_set_password_form(self):
        """Auditor con must_change_password=True ve formulario de cambio de contraseña."""
        self.auditor_user.must_change_password = True
        self.auditor_user.save(update_fields=['must_change_password'])
        response = self._post_login('auditor@test.com', self.DEFAULT_PASSWORD)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['show_set_password'])

    def test_auditor_set_password_redirects_to_audit_dashboard(self):
        """Auditor que cambia contraseña redirige a audit_dashboard."""
        self.auditor_user.must_change_password = True
        self.auditor_user.save(update_fields=['must_change_password'])
        self._post_login('auditor@test.com', self.DEFAULT_PASSWORD)
        response = self.client.post(
            reverse('login'),
            {
                'step': 'set_password',
                'new_password': 'NewAudit123!',
                'confirm_password': 'NewAudit123!',
            },
        )
        self.assertRedirects(
            response, reverse('audit_dashboard'), fetch_redirect_response=False
        )


# ─────────────────────────────────────────────────────────────────────────────
# BLOQUE 3.6 — Logout
# ─────────────────────────────────────────────────────────────────────────────

class LogoutTest(BaseTestCase):

    def test_logout_redirects_to_login(self):
        """Logout redirige a la página de login."""
        self.login(self.employee_user)
        response = self.client.get(reverse('logout'))
        self.assertRedirects(
            response, reverse('login'), fetch_redirect_response=False
        )

    def test_logout_clears_session(self):
        """Logout elimina al usuario de la sesión."""
        self.login(self.employee_user)
        self.client.get(reverse('logout'))
        self.assertNotIn(SESSION_KEY, self.client.session)

    def test_logout_creates_audit_log(self):
        """Logout crea AuditLog con reason='Logout'."""
        self.login(self.employee_user)
        self.client.get(reverse('logout'))
        exists = AuditLog.objects.filter(
            user=self.employee_user,
            reason='Logout',
        ).exists()
        self.assertTrue(exists)

    def test_anonymous_logout_redirects_to_login(self):
        """Usuario no autenticado que accede a logout es redirigido a login."""
        response = self.client.get(reverse('logout'))
        self.assertEqual(response.status_code, 302)
        self.assertIn('/', response['Location'])