class Usuario:
    def __init__(self, name, buttons, rol, version):
        self.name = name
        self.buttons = buttons
        self.rol = rol
        self.version = version

    def __str__(self):
        return f"{self.name} ({self.rol}) ({self.version}) Btn: {self.buttons}"

    def permisos(self):
        all_keys = [
            'Nueva_Orden','Nueva_Nota','Nueva_Parte',
            'Ver_Nota','Ver_Parte','Nuevo_Servicio','Ver_Servicio','Reporte'
        ]
        base = {k: False for k in all_keys}
        if isinstance(self.rol, str) and self.rol.strip().lower() in ('administrador', 'admin'):
            for k in base: base[k] = True
            return base
        btns = self.buttons
        if isinstance(btns, (list, tuple, set)):
            labels = {str(x).strip().lower() for x in btns}
            for k in base: base[k] = (k.lower() in labels)
            return base
        if isinstance(btns, str):
            labels = {x.strip().lower() for x in btns.split(',')}
            for k in base: base[k] = (k.lower() in labels)
            return base
        if isinstance(btns, int):
            if btns >= len(all_keys):
                for k in base: base[k] = True
            else:
                n = btns
                for i, k in enumerate(all_keys):
                    if n & (1 << i): base[k] = True
            return base
        return base

def usuarios_default():
    return [Usuario(
        name='cib700_01',
        buttons=['Nueva_Orden','Nueva_Nota','Nueva_Parte','Ver_Nota','Ver_Parte','Nuevo_Servicio','Ver_Servicio','Reporte'],
        rol='Administrador',
        version='local'
    )]
