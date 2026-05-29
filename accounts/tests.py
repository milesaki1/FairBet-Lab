from datetime import date, timedelta
import unittest
from django.contrib.auth.models import User
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from .models import PerfilUsuario
from config.choices import EstadoPerfil

class RegistroUsuarioAPITests(APITestCase):

    def setUp(self):
        self.registro_url = reverse('api_register')
        self.login_url = reverse('api_login')
        
        # Fecha de nacimiento válida (mayor de 18 años)
        self.fecha_valida = (date.today() - timedelta(days=365 * 20)).isoformat()
        # Fecha de nacimiento menor de edad
        self.fecha_menor = (date.today() - timedelta(days=365 * 15)).isoformat()
        
        # DNI Válido: '12345678'
        self.dni_valido = '12345678'
        
        # DNI Válido 2: '10000000'
        self.dni_valido_2 = '10000000'

    def test_registro_exitoso(self):
        """
        Prueba que un usuario mayor de edad con un DNI correcto se registre con éxito.
        """
        data = {
            'username': 'juanperez',
            'email': 'juan@correo.com',
            'password': 'password123',
            'first_name': 'Juan',
            'last_name': 'Pérez',
            'fecha_nacimiento': self.fecha_valida,
            'dni': self.dni_valido,
        }
        
        response = self.client.post(self.registro_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        # Verificar creación en base de datos
        user = User.objects.get(username='juanperez')
        self.assertIsNotNone(user.perfil)
        self.assertEqual(user.perfil.dni, self.dni_valido)
        self.assertEqual(user.perfil.estado, EstadoPerfil.VERIFICADO)
        # Verificar límites de depósito por defecto
        self.assertEqual(user.perfil.limite_deposito_diario, 1000.0000)
        self.assertEqual(user.perfil.limite_deposito_semanal, 5000.0000)
        self.assertEqual(user.perfil.limite_deposito_mensual, 20000.0000)

    def test_registro_menor_de_edad_falla(self):
        """
        Prueba que se deniegue el registro si el usuario es menor de 18 años.
        """
        data = {
            'username': 'juanito',
            'email': 'juanito@correo.com',
            'password': 'password123',
            'first_name': 'Juanito',
            'last_name': 'Pérez',
            'fecha_nacimiento': self.fecha_menor,
            'dni': self.dni_valido_2,
        }
        
        response = self.client.post(self.registro_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('fecha_nacimiento', str(response.data) or str(response.data.get('non_field_errors', '')))

    def test_registro_dni_no_numerico_falla(self):
        """
        Prueba que falle el registro si el número de DNI contiene letras o no tiene 8 dígitos.
        """
        data = {
            'username': 'maria',
            'email': 'maria@correo.com',
            'password': 'password123',
            'first_name': 'María',
            'last_name': 'López',
            'fecha_nacimiento': self.fecha_valida,
            'dni': '1234567A',  # DNI con letras
        }
        
        response = self.client.post(self.registro_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_login_correcto(self):
        """
        Prueba que un usuario verificado pueda iniciar sesión.
        """
        # Crear usuario previo
        user = User.objects.create_user(username='loginuser', password='password123', email='login@correo.com')
        PerfilUsuario.objects.create(
            user=user,
            fecha_nacimiento=date.today() - timedelta(days=365*20),
            dni=self.dni_valido_2,
            estado=EstadoPerfil.VERIFICADO
        )
        
        data = {
            'username': 'loginuser',
            'password': 'password123'
        }
        response = self.client.post(self.login_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('user', response.data)

    def test_login_usuario_bloqueado_falla(self):
        """
        Prueba que un usuario con perfil en estado 'bloqueado' no pueda iniciar sesión.
        """
        user = User.objects.create_user(username='blockeduser', password='password123', email='blocked@correo.com')
        PerfilUsuario.objects.create(
            user=user,
            fecha_nacimiento=date.today() - timedelta(days=365*20),
            dni=self.dni_valido_2,
            estado=EstadoPerfil.BLOQUEADO
        )
        
        data = {
            'username': 'blockeduser',
            'password': 'password123'
        }
        response = self.client.post(self.login_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_login_usuario_autoexcluido_falla(self):
        """
        Prueba que un usuario autoexcluido no pueda iniciar sesión durante el período de autoexclusión.
        """
        user = User.objects.create_user(username='excludeduser', password='password123', email='excluded@correo.com')
        from accounts.models import TipoAutoexclusion
        PerfilUsuario.objects.create(
            user=user,
            fecha_nacimiento=date.today() - timedelta(days=365*20),
            dni=self.dni_valido_2,
            tipo_autoexclusion=TipoAutoexclusion.DIAS_7
        )
        
        data = {
            'username': 'excludeduser',
            'password': 'password123'
        }
        response = self.client.post(self.login_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


from accounts.forms import RegistroForm

class RegistroFormTests(APITestCase):
    def test_passwords_no_coinciden(self):
        data = {
            'username': 'testuser',
            'email': 'test@correo.com',
            'first_name': 'Test',
            'last_name': 'User',
            'password': 'password123',
            'password_confirm': 'differentpass',
            'fecha_nacimiento': (date.today() - timedelta(days=365 * 20)).isoformat(),
            'dni': '12345678',
        }
        form = RegistroForm(data)
        self.assertFalse(form.is_valid())
        self.assertIn('password_confirm', form.errors)
        self.assertEqual(form.errors['password_confirm'], ['Las contraseñas no coinciden.'])


from accounts.models import TipoAutoexclusion, TipoLimite, PerfilUsuario

class JuegoResponsableTests(APITestCase):

    def setUp(self):
        self.user = User.objects.create_user(username='player', password='password123', email='player@correo.com')
        self.perfil = PerfilUsuario.objects.create(
            user=self.user,
            fecha_nacimiento=date.today() - timedelta(days=365*25),
            dni='87654321',
            estado=EstadoPerfil.VERIFICADO
        )

    def test_reduccion_limite_inmediato(self):
        """
        Si el usuario reduce un límite, se debe aplicar inmediatamente.
        """
        self.perfil.limite_deposito_diario = 100.0
        self.perfil.save()

        # Solicitar reducción (de 100 a 50)
        self.perfil.solicitar_cambio_limite(TipoLimite.DIARIO, 50.0)
        self.assertEqual(self.perfil.limite_deposito_diario, 50.0)
        self.assertIsNone(self.perfil.limite_pendiente)

    def test_incremento_limite_cooldown(self):
        """
        Si el usuario incrementa un límite, no se debe aplicar al instante.
        Debe guardarse en los campos pendientes.
        """
        self.perfil.limite_deposito_diario = 100.0
        self.perfil.save()

        # Solicitar incremento (de 100 a 200)
        self.perfil.solicitar_cambio_limite(TipoLimite.DIARIO, 200.0)
        self.assertEqual(self.perfil.limite_deposito_diario, 100.0)  # Sigue en 100
        self.assertEqual(self.perfil.limite_pendiente, 200.0)
        self.assertEqual(self.perfil.tipo_limite_pendiente, TipoLimite.DIARIO)
        self.assertIsNotNone(self.perfil.fecha_solicitud_incremento)

    def test_solo_un_incremento_pendiente_a_la_vez(self):
        """
        Solo permitir un incremento pendiente a la vez.
        """
        self.perfil.limite_deposito_diario = 100.0
        self.perfil.limite_deposito_semanal = 500.0
        self.perfil.save()

        self.perfil.solicitar_cambio_limite(TipoLimite.DIARIO, 200.0)
        
        # Intentar otro incremento (semanal de 500 a 1000) debe fallar
        from django.core.exceptions import ValidationError
        with self.assertRaises(ValidationError):
            self.perfil.solicitar_cambio_limite(TipoLimite.SEMANAL, 1000.0)

    def test_autoexclusion_calculo_automatico(self):
        """
        Si el usuario selecciona 7, 30 o 90 días, se calcula autoexclusion_hasta automáticamente.
        """
        # 7 días
        self.perfil.tipo_autoexclusion = TipoAutoexclusion.DIAS_7
        self.perfil.save()
        self.assertIsNotNone(self.perfil.fecha_autoexclusion_hasta)
        self.assertEqual(self.perfil.estado, EstadoPerfil.AUTOEXCLUIDO)
        self.assertTrue(self.perfil.esta_autoexcluido)

        # 30 días
        self.perfil.tipo_autoexclusion = TipoAutoexclusion.DIAS_30
        self.perfil.save()
        self.assertIsNotNone(self.perfil.fecha_autoexclusion_hasta)
        self.assertTrue(self.perfil.esta_autoexcluido)

    def test_autoexclusion_indefinida(self):
        """
        Si selecciona indefinida, no permite reversión y deja autoexclusion_hasta en null.
        """
        self.perfil.tipo_autoexclusion = TipoAutoexclusion.INDEFINIDA
        self.perfil.save()
        self.assertIsNone(self.perfil.fecha_autoexclusion_hasta)
        self.assertTrue(self.perfil.esta_autoexcluido)

        # Intentar revertir debe fallar
        self.perfil.tipo_autoexclusion = TipoAutoexclusion.NINGUNA
        from django.core.exceptions import ValidationError
        with self.assertRaises(ValidationError):
            self.perfil.save()

    def test_aplicar_limite_pendiente_exito(self):
        """
        Si pasaron las 24 horas, aplicar_limite_pendiente debe aplicar el límite.
        """
        from django.utils import timezone
        self.perfil.limite_deposito_diario = 100.0
        self.perfil.save()

        # Solicitar incremento (cooldown)
        self.perfil.solicitar_cambio_limite(TipoLimite.DIARIO, 200.0)
        
        # Simular que pasaron 25 horas
        self.perfil.fecha_solicitud_incremento = timezone.now() - timedelta(hours=25)
        self.perfil.save()

        # Ejecutar la función
        self.assertTrue(self.perfil.aplicar_limite_pendiente())
        self.assertEqual(self.perfil.limite_deposito_diario, 200.0)
        self.assertIsNone(self.perfil.limite_pendiente)

    def test_aplicar_limite_pendiente_antes_de_tiempo(self):
        """
        Si no han pasado las 24 horas, aplicar_limite_pendiente no debe hacer nada.
        """
        self.perfil.limite_deposito_diario = 100.0
        self.perfil.save()

        # Solicitar incremento
        self.perfil.solicitar_cambio_limite(TipoLimite.DIARIO, 200.0)

        # Ejecutar la función (solo ha pasado 0 tiempo)
        self.assertFalse(self.perfil.aplicar_limite_pendiente())
        self.assertEqual(self.perfil.limite_deposito_diario, 100.0)

