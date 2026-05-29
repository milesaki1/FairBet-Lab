from datetime import date
from django.core.exceptions import ValidationError


def validar_dni(dni, digito_verificador=None):
    """
    Valida la estructura de un DNI peruano (8 dígitos) y su dígito verificador.
    """
    if not dni or not dni.isdigit() or len(dni) != 8:
        raise ValidationError("El DNI debe contener exactamente 8 dígitos numéricos.")

    if digito_verificador is not None:
        try:
            dv = int(digito_verificador)
        except (ValueError, TypeError):
            raise ValidationError(
                "El dígito verificador debe ser un número del 0 al 9."
            )

        pesos = [3, 2, 7, 6, 5, 4, 3, 2]
        suma_productos = 0

        for i in range(8):
            suma_productos += int(dni[i]) * pesos[i]

        residuo = suma_productos % 11
        tabla_residuos = [6, 5, 4, 3, 2, 1, 0, 9, 8, 7, 6]

        if tabla_residuos[residuo] != dv:
            raise ValidationError(
                "El DNI ingresado o su dígito verificador es incorrecto."
            )


def validar_mayor_edad(fecha_nacimiento):
    """
    Valida que la fecha de nacimiento corresponda a un usuario mayor de 18 años.
    """
    if not fecha_nacimiento:
        raise ValidationError("Debe proporcionar su fecha de nacimiento.")

    today = date.today()
    # Calcular edad
    edad = (
        today.year
        - fecha_nacimiento.year
        - ((today.month, today.day) < (fecha_nacimiento.month, fecha_nacimiento.day))
    )
    if edad < 18:
        raise ValidationError(
            "Debe ser mayor de edad (mínimo 18 años) para registrarse."
        )
