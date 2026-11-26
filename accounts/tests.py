from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

User = get_user_model()


class AccountsAuthTests(TestCase):
    """Pruebas de registro, inicio de sesión, panel protegido y cierre de sesión."""

    def setUp(self):
        self.registro_url = reverse('accounts:registro')
        self.login_url = reverse('accounts:login')
        self.panel_url = reverse('accounts:panel')
        self.logout_url = reverse('accounts:logout')

    def test_1_registro_valido(self):
        """Un registro válido crea el usuario y redirige a iniciar sesión."""
        respuesta_get = self.client.get(self.registro_url)
        self.assertEqual(respuesta_get.status_code, 200)
        self.assertTemplateUsed(respuesta_get, 'accounts/registro.html')
        self.assertEqual(
            list(respuesta_get.context['form'].fields.keys()),
            ['username', 'password1', 'password2'],
        )
        self.assertContains(respuesta_get, 'Crear cuenta')
        self.assertContains(respuesta_get, 'Iniciar sesión')

        respuesta_post = self.client.post(
            self.registro_url,
            {
                'username': 'docente_demo',
                'password1': 'ClaveDocente2026!',
                'password2': 'ClaveDocente2026!',
            },
        )
        self.assertRedirects(respuesta_post, self.login_url)
        self.assertTrue(User.objects.filter(username='docente_demo').exists())

    def test_2_registro_contrasenas_distintas_sin_crear_cuenta(self):
        """Si las contraseñas no coinciden, no se crea cuenta y se muestran errores."""
        respuesta = self.client.post(
            self.registro_url,
            {
                'username': 'docente_fallido',
                'password1': 'ClaveDocente2026!',
                'password2': 'OtraClaveDistinta99!',
            },
        )
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(User.objects.count(), 0)
        self.assertFalse(respuesta.context['form'].is_valid())
        self.assertIn('password2', respuesta.context['form'].errors)

    def test_3_visita_anonima_al_panel(self):
        """Un visitante sin sesión que entra a /panel/ es redirigido a /iniciar-sesion/."""
        respuesta = self.client.get(self.panel_url)
        self.assertRedirects(respuesta, f'{self.login_url}?next={self.panel_url}')

    def test_4_usuario_inexistente(self):
        """Iniciar sesión con un usuario que no existe falla y mantiene sesión anónima."""
        respuesta = self.client.post(
            self.login_url,
            {
                'username': 'docente_inexistente',
                'password': 'ClaveDocente2026!',
            },
        )
        self.assertEqual(respuesta.status_code, 200)
        self.assertNotIn('_auth_user_id', self.client.session)
        self.assertTrue(respuesta.context['form'].errors)

    def test_5_contrasena_incorrecta(self):
        """Iniciar sesión con contraseña incorrecta falla y no autentica."""
        User.objects.create_user(
            username='docente_prueba',
            password='ClaveCorrecta2026!',
        )
        respuesta = self.client.post(
            self.login_url,
            {
                'username': 'docente_prueba',
                'password': 'ClaveEquivocada000!',
            },
        )
        self.assertEqual(respuesta.status_code, 200)
        self.assertNotIn('_auth_user_id', self.client.session)
        self.assertTrue(respuesta.context['form'].errors)

    def test_6_acceso_valido(self):
        """Con credenciales válidas inicia sesión y muestra el usuario en /panel/."""
        usuario = User.objects.create_user(
            username='docente_activo',
            password='ClaveCorrecta2026!',
        )
        respuesta_login = self.client.post(
            self.login_url,
            {
                'username': 'docente_activo',
                'password': 'ClaveCorrecta2026!',
            },
            follow=True,
        )
        self.assertRedirects(respuesta_login, self.panel_url)
        self.assertTemplateUsed(respuesta_login, 'accounts/panel.html')
        self.assertContains(respuesta_login, 'docente_activo')
        self.assertContains(respuesta_login, 'Cerrar sesión')
        self.assertNotContains(respuesta_login, usuario.password)

    def test_7_cierre_sesion_y_nueva_visita_al_panel(self):
        """Cerrar sesión por POST invalida el acceso y /panel/ vuelve a pedir login."""
        User.objects.create_user(
            username='docente_cierre',
            password='ClaveCorrecta2026!',
        )
        self.client.login(
            username='docente_cierre',
            password='ClaveCorrecta2026!',
        )
        respuesta_panel = self.client.get(self.panel_url)
        self.assertEqual(respuesta_panel.status_code, 200)

        respuesta_logout = self.client.post(self.logout_url)
        self.assertRedirects(respuesta_logout, self.login_url)
        self.assertNotIn('_auth_user_id', self.client.session)

        respuesta_reingreso = self.client.get(self.panel_url)
        self.assertRedirects(
            respuesta_reingreso,
            f'{self.login_url}?next={self.panel_url}',
        )
