import re
from fastapi import FastAPI, HTTPException, Depends
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.requests import Request
from starlette.middleware.sessions import SessionMiddleware
import uvicorn
import os
import random

app = FastAPI()

# Añadir soporte para sesiones
app.add_middleware(SessionMiddleware, secret_key="mysecretkey")

# Configuración para servir archivos estáticos (CSS, JS)
app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/imagenes", StaticFiles(directory="imagenes"), name="imagenes")

# Configuración para usar plantillas (HTML)
templates = Jinja2Templates(directory="templates")

# Expresión regular para validar los nombres de usuario
username_pattern = re.compile(r"^[a-zA-Z][a-zA-Z\s]*$")

# Expresión regular para validar contraseñas (sin espacios ni saltos de línea)
password_pattern = re.compile(r"^\S+$")

# Archivos para almacenar los usuarios, administradores y sorteos
USER_DB = "users.txt"
ADMIN_DB = "admin.txt"
SORTEOS_DB = "sorteos.txt"

# Función para verificar si el usuario está autenticado
def get_current_user(request: Request):
    return request.session.get("user")

# Función para verificar si el usuario es administrador
def is_admin(username, password):
    try:
        with open(ADMIN_DB, "r", encoding='utf-8') as f:
            for line in f:
                admin_user, admin_pass = line.strip().split(":")
                if admin_user == username and admin_pass == password:
                    return True
    except FileNotFoundError:
        return False
    return False

def leer_sorteos():
    sorteos = []
    try:
        with open(SORTEOS_DB, "r", encoding='utf-8') as f:
            for line in f:
                partes = line.strip().split("|")
                if len(partes) >= 4:
                    nombre, descripcion, precio, sobre_regalo = partes[:4]
                    
                    # Verificar si el campo 'inscripciones_abiertas' está presente
                    inscripciones_abiertas = False  # Valor por defecto
                    if len(partes) > 4:
                        inscripciones_abiertas = True if partes[4] == 'True' else False
                    
                    # Verificar si el campo de participantes está presente
                    participantes = []
                    if len(partes) > 5 and partes[5]:  # Verifica si partes[5] existe y no está vacío
                        participantes = partes[5].split(",")
                    
                    sorteos.append({
                        "nombre": nombre,
                        "descripcion": descripcion,
                        "precio": precio,
                        "sobre_regalo": sobre_regalo,
                        "inscripciones_abiertas": inscripciones_abiertas,
                        "participantes": participantes,                        
                    })
    except FileNotFoundError:
        pass
    return sorteos




def escribir_sorteos(sorteos):
    with open(SORTEOS_DB, "w", encoding='utf-8') as f:
        for sorteo in sorteos:
            participantes_str = ",".join(sorteo["participantes"])
            inscripciones_abiertas_str = 'True' if sorteo["inscripciones_abiertas"] else 'False'
            f.write(f'{sorteo["nombre"]}|{sorteo["descripcion"]}|{sorteo["precio"]}|{sorteo["sobre_regalo"]}|{inscripciones_abiertas_str}|{participantes_str}\n')


# Ruta POST para eliminar un sorteo (solo administradores)
@app.post("/eliminar-sorteo")
async def eliminar_sorteo(request: Request):
    form_data = await request.form()
    nombre_sorteo = form_data.get("nombre_sorteo")
    user = get_current_user(request)

    if not is_admin(user, request.session.get("password")):
        return JSONResponse(status_code=403, content={"error": "Acceso denegado"})

    # Leer los sorteos
    sorteos = leer_sorteos()

    # Eliminar el sorteo de la lista
    sorteos = [s for s in sorteos if s["nombre"] != nombre_sorteo]

    # Reescribir los sorteos
    escribir_sorteos(sorteos)

    return JSONResponse(status_code=200, content={"message": f"Sorteo {nombre_sorteo} eliminado con éxito"})


# Ruta POST para eliminar un participante de un sorteo (solo administradores)
@app.post("/eliminar-participante")
async def eliminar_participante(request: Request):
    form_data = await request.form()
    nombre_sorteo = form_data.get("nombre_sorteo")
    participante = form_data.get("participante")
    user = get_current_user(request)

    if not is_admin(user, request.session.get("password")):
        return JSONResponse(status_code=403, content={"error": "Acceso denegado"})

    # Leer los sorteos
    sorteos = leer_sorteos()

    # Buscar el sorteo y eliminar el participante
    for sorteo in sorteos:
        if sorteo["nombre"] == nombre_sorteo:
            if participante in sorteo["participantes"]:
                sorteo["participantes"].remove(participante)
                escribir_sorteos(sorteos)
                return JSONResponse(status_code=200, content={"message": f"Participante {participante} eliminado del sorteo {nombre_sorteo}"})

    return JSONResponse(status_code=404, content={"error": "Sorteo o participante no encontrado"})



# Ruta principal para mostrar los sorteos y permitir inscripción
@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    user = get_current_user(request)
    if not user:
        return templates.TemplateResponse("login.html", {"request": request})
    if is_admin(request.session.get("user"), request.session.get("password")):
        return RedirectResponse("/admin-page", status_code=302)
    # Leer los sorteos existentes
    sorteos = leer_sorteos()

    return templates.TemplateResponse("index.html", {"request": request, "user": user, "sorteos": sorteos})

@app.get("/contribuidores.html", response_class=HTMLResponse)
async def contribuidores(request: Request):
    return templates.TemplateResponse("contribuidores.html", {"request": request})


# Ruta GET para mostrar el formulario de registro
@app.get("/register-page", response_class=HTMLResponse)
async def register_page(request: Request):
    return templates.TemplateResponse("register.html", {"request": request})

# Ruta GET para mostrar la página de administración (solo para administradores)
@app.get("/admin-page", response_class=HTMLResponse)
async def admin_page(request: Request):
    user = get_current_user(request)
    if not user or not is_admin(request.session.get("user"), request.session.get("password")):
        return RedirectResponse("/", status_code=302)  # Redirigir si no es administrador

    # Leer los sorteos existentes
    sorteos = leer_sorteos()

    return templates.TemplateResponse("index-admin.html", {"request": request, "user": user, "sorteos": sorteos})

# Ruta GET para mostrar el formulario de crear sorteo (solo administradores)
@app.get("/admin-form", response_class=HTMLResponse)
async def admin_form(request: Request):
    user = get_current_user(request)
    if not is_admin(user, request.session.get("password")):
        return RedirectResponse("/", status_code=302)  # Redirigir si no es administrador
    return templates.TemplateResponse("admin-form.html", {"request": request})


# Ruta POST para crear un nuevo sorteo (solo administradores)
@app.post("/crear-sorteo")
async def crear_sorteo(request: Request):
    user = get_current_user(request)
    if not user or not is_admin(request.session.get("user"), request.session.get("password")):
        return JSONResponse(status_code=403, content={"error": "Acceso denegado"})

    form_data = await request.form()
    nombre = form_data.get("nombre")
    descripcion = form_data.get("descripcion")
    precio = form_data.get("precio")
    sobre_regalo = form_data.get("sobre_regalo")

    if not nombre or not descripcion or not precio or not sobre_regalo:
        return JSONResponse(status_code=400, content={"error": "Todos los campos son obligatorios"})

    # Guardar el sorteo en el archivo sorteos.txt
    with open(SORTEOS_DB, "a") as f:
        f.write(f"{nombre}|{descripcion}|{precio}|{sobre_regalo}|{'True'}\n")

    return JSONResponse(status_code=200, content={"message": "Sorteo creado con éxito"})

# Ruta GET para mostrar el formulario de modificación de un sorteo
@app.get("/modificar-sorteo/{nombre}", response_class=HTMLResponse)
async def modificar_sorteo_page(request: Request, nombre: str):
    user = get_current_user(request)

    # Verificar si el usuario es administrador
    if not is_admin(user, request.session.get("password")):
        return RedirectResponse("/", status_code=302)

    # Leer los sorteos existentes
    sorteos = leer_sorteos()
    sorteo = next((s for s in sorteos if s["nombre"] == nombre), None)

    if not sorteo:
        return JSONResponse(status_code=404, content={"error": "Sorteo no encontrado"})

    # Renderizar la página de modificación del sorteo con los datos
    return templates.TemplateResponse("mod-sorteo.html", {"request": request, "sorteo": sorteo})

# Ruta POST para modificar un sorteo existente
@app.post("/modificar-sorteo")
async def modificar_sorteo(request: Request):
    form_data = await request.form()
    nuevo_nombre = form_data.get("nombre")
    descripcion = form_data.get("descripcion")
    precio = form_data.get("precio")
    sobre_regalo = form_data.get("sobre_regalo")
    inscripciones_abiertas = form_data.get("inscripciones_abiertas")
    user = get_current_user(request)

    # Verificar si el usuario es administrador
    if not is_admin(user, request.session.get("password")):
        return JSONResponse(status_code=403, content={"error": "Acceso denegado"})

    # Leer los sorteos existentes
    sorteos = leer_sorteos()

    # Buscar el sorteo a modificar
    for sorteo in sorteos:
        if sorteo["nombre"] == nuevo_nombre:
            # Actualizar los datos del sorteo
            sorteo["descripcion"] = descripcion
            sorteo["precio"] = precio
            sorteo["sobre_regalo"] = sobre_regalo
            sorteo["inscripciones_abiertas"] = inscripciones_abiertas
            break

    # Reescribir los sorteos con los datos actualizados
    escribir_sorteos(sorteos)

    return JSONResponse(status_code=200, content={"message": "Sorteo modificado con éxito"})



@app.post("/empezar-sorteo")
async def empezar_sorteo(request: Request):
    form_data = await request.form()
    nombre_sorteo = form_data.get("nombre_sorteo")
    user = get_current_user(request)

    # Verificar si el usuario es administrador
    if not is_admin(user, request.session.get("password")):
        return JSONResponse(status_code=403, content={"error": "Acceso denegado"})

    # Leer los sorteos existentes
    sorteos = leer_sorteos()

    # Buscar el sorteo en cuestión
    sorteo = next((s for s in sorteos if s["nombre"] == nombre_sorteo), None)

    if not sorteo:
        return JSONResponse(status_code=404, content={"error": "Sorteo no encontrado"})

    # Obtener la lista de participantes
    participantes = sorteo["participantes"]

    if len(participantes) < 2:
        return JSONResponse(status_code=400, content={"error": "Debe haber al menos dos participantes para iniciar el sorteo."})

    # Desactivar inscripción de nuevos participantes solo para este sorteo
    sorteo["inscripciones_abiertas"] = False

    # Asignar aleatoriamente los participantes
    asignaciones = asignar_participantes(participantes)

    # Guardar las asignaciones en asignaciones.txt
    guardar_asignaciones(nombre_sorteo, asignaciones)

    # Reescribir los sorteos para desactivar nuevas inscripciones solo para este sorteo
    escribir_sorteos(sorteos)

    return JSONResponse(status_code=200, content={"message": "Sorteo iniciado y participantes asignados con éxito."})

@app.post("/reiniciar-sorteo")
async def reiniciar_sorteo(request: Request):
    form_data = await request.form()
    nombre_sorteo = form_data.get("nombre_sorteo")
    user = get_current_user(request)

    # Verificar si el usuario es administrador
    if not is_admin(user, request.session.get("password")):
        return JSONResponse(status_code=403, content={"error": "Acceso denegado"})

    # Leer los sorteos existentes
    sorteos = leer_sorteos()

    # Buscar el sorteo en cuestión
    sorteo = next((s for s in sorteos if s["nombre"] == nombre_sorteo), None)

    if not sorteo:
        return JSONResponse(status_code=404, content={"error": "Sorteo no encontrado"})

    # Obtener la lista de participantes
    participantes = sorteo["participantes"]

    if len(participantes) < 2:
        return JSONResponse(status_code=400, content={"error": "Debe haber al menos dos participantes para reiniciar el sorteo."})

    # Eliminar la asignación existente del archivo "asignaciones.txt"
    eliminar_asignacion_existente(nombre_sorteo)

    # Asignar aleatoriamente los participantes de nuevo
    asignaciones = asignar_participantes(participantes)

    # Guardar las nuevas asignaciones en "asignaciones.txt"
    guardar_asignaciones(nombre_sorteo, asignaciones)

    return JSONResponse(status_code=200, content={"message": "Sorteo reiniciado y nuevas asignaciones realizadas con éxito."})


# Función para asignar participantes de manera aleatoria
def asignar_participantes(participantes):
    random.shuffle(participantes)  # Mezclar aleatoriamente los participantes
    asignaciones = []
    for i in range(len(participantes)):
        asignado_a = participantes[(i + 1) % len(participantes)]  # Asigna al siguiente en la lista
        asignaciones.append((participantes[i], asignado_a))
    return asignaciones

def eliminar_asignacion_existente(nombre_sorteo):
    try:
        # Leer todas las asignaciones del archivo
        with open("asignaciones.txt", "r", encoding='utf-8') as f:
            asignaciones = f.readlines()

        # Filtrar las asignaciones, eliminando las del sorteo actual
        nuevas_asignaciones = [line for line in asignaciones if not line.startswith(nombre_sorteo)]

        # Escribir las asignaciones restantes de vuelta al archivo
        with open("asignaciones.txt", "w", encoding='utf-8') as f:
            f.writelines(nuevas_asignaciones)

    except FileNotFoundError:
        pass  # Si no existe el archivo, no hacemos nada


# Función para guardar las asignaciones en asignaciones.txt
def guardar_asignaciones(nombre_sorteo, asignaciones):
    with open("asignaciones.txt", "a", encoding='utf-8') as f:
        asignaciones_str = ",".join([f'"{a[0]}"-"{a[1]}"' for a in asignaciones])
        f.write(f'{nombre_sorteo}|{asignaciones_str}\n')

@app.get("/resultados-sorteo/{nombre_sorteo}")
async def obtener_resultados_sorteo(nombre_sorteo: str):
    try:
        with open("asignaciones.txt", "r", encoding='utf-8') as f:
            for line in f:
                sorteo_nombre, asignaciones_str = line.strip().split("|")
                if sorteo_nombre == nombre_sorteo:
                    asignaciones = asignaciones_str.split(",")
                    return JSONResponse(status_code=200, content={"resultados": asignaciones})
        return JSONResponse(status_code=404, content={"error": "Sorteo no encontrado o no tiene asignaciones"})
    except FileNotFoundError:
        return JSONResponse(status_code=404, content={"error": "Archivo de asignaciones no encontrado"})


# Ruta para que los participantes vean a quién les ha tocado
# Ruta para ver la asignación del sorteo
@app.get("/ver-asignacion/{nombre_sorteo}/{participante}", response_class=HTMLResponse)
async def ver_asignacion(request: Request, nombre_sorteo: str, participante: str):
    try:
        # Leer el archivo de asignaciones
        with open("asignaciones.txt", "r", encoding='utf-8') as f:
            for line in f:
                sorteo_nombre, asignaciones_str = line.strip().split("|")
                if sorteo_nombre == nombre_sorteo:
                    asignaciones = asignaciones_str.split(",")
                    for asignacion in asignaciones:
                        participante_1, participante_2 = asignacion.replace('"', '').split("-")
                        if participante_1 == participante:
                            # Renderizar la página con la persona asignada
                            return templates.TemplateResponse("resultado.html", {
                                "request": request,
                                "nombre": participante_2
                            })
    except FileNotFoundError:
        return JSONResponse(status_code=404, content={"error": "Asignaciones no encontradas"})

    return JSONResponse(status_code=404, content={"error": "Participante no encontrado en este sorteo"})

@app.post("/reiniciar-sorteo/{nombre_sorteo}")
async def reiniciar_sorteo(nombre_sorteo: str):
    try:
        # Leer todas las asignaciones
        asignaciones = []
        with open("asignaciones.txt", "r", encoding='utf-8') as f:
            asignaciones = f.readlines()

        # Eliminar la asignación del sorteo correspondiente
        asignaciones = [line for line in asignaciones if not line.startswith(nombre_sorteo)]

        # Guardar las asignaciones restantes
        with open("asignaciones.txt", "w", encoding='utf-8') as f:
            f.writelines(asignaciones)

        # Leer los sorteos y asignar de nuevo
        sorteos = leer_sorteos()  # Función que ya tienes para leer sorteos
        sorteo = next((s for s in sorteos if s["nombre"] == nombre_sorteo), None)

        if not sorteo:
            return JSONResponse(status_code=404, content={"error": "Sorteo no encontrado"})

        participantes = sorteo["participantes"]
        if len(participantes) < 2:
            return JSONResponse(status_code=400, content={"error": "Debe haber al menos dos participantes para iniciar el sorteo."})

        # Reasignar los participantes de manera aleatoria
        nueva_asignacion = asignar_participantes(participantes)  # Función que debes implementar para reasignar

        # Guardar la nueva asignación en el archivo
        with open("asignaciones.txt", "a", encoding='utf-8') as f:
            f.write(f'{nombre_sorteo}|"{"-".join(nueva_asignacion)}"\n')

        return JSONResponse(status_code=200, content={"message": "Sorteo reiniciado y participantes reasignados con éxito."})

    except Exception as e:
        return JSONResponse(status_code=500, content={"error": "Error al reiniciar el sorteo"})


# Ruta POST para procesar el inicio de sesión
@app.post("/login")
async def login(request: Request):
    form_data = await request.form()
    username = form_data.get("username")
    password = form_data.get("password")
    

    # Verificar si faltan los campos
    if not username or not password:
        return JSONResponse(status_code=400, content={"error": "Debes completar ambos campos"})

    # Verificar el formato del nombre de usuario
    if not username_pattern.match(username):
        return JSONResponse(status_code=400, content={"error": "Nombre de usuario inválido. Solo se permiten letras y espacios."})

    # Verificar el formato de la contraseña
    if not password_pattern.match(password):
        return JSONResponse(status_code=400, content={"error": "Contraseña inválida. No puede contener espacios ni saltos de línea."})

    # Comprobar si el usuario existe y la autenticación es correcta
    if authenticate_user(username, password):
        request.session["user"] = username
        request.session["password"] = password  # Guardar la contraseña en la sesión para la verificación del admin
        return JSONResponse(status_code=200, content={"message": "Has iniciado sesión con éxito"})
    
    return JSONResponse(status_code=400, content={"error": "Usuario o contraseña incorrectos"})

# Ruta POST para procesar el registro de nuevos usuarios
# Ruta POST para procesar el registro de nuevos usuarios
@app.post("/register")
async def register(request: Request):
    form_data = await request.form()
    username = form_data.get("username")
    password = form_data.get("password")

    # Verificar si faltan los campos
    if not username or not password:
        return JSONResponse(status_code=400, content={"error": "Debes completar ambos campos"})

    # Verificar el formato del nombre de usuario
    if not username_pattern.match(username):
        return JSONResponse(status_code=400, content={"error": "Nombre de usuario inválido. Solo se permiten letras y espacios."})

    # Verificar el formato de la contraseña
    if not password_pattern.match(password):
        return JSONResponse(status_code=400, content={"error": "Contraseña inválida. No puede contener espacios ni saltos de línea."})

    # Verificar si el usuario ya existe
    if user_exists(username):
        return JSONResponse(status_code=400, content={"error": "El nombre de usuario ya existe"})

    # Guardar el usuario en el archivo
    with open(USER_DB, "a", encoding='utf-8') as f:
        f.write(f"{username}:{password}\n")
    
    request.session["user"] = username
    return JSONResponse(status_code=200, content={"message": "Registro exitoso, has iniciado sesión"})


# Ruta para cerrar sesión
@app.get("/logout")
async def logout(request: Request):
    request.session.pop("user", None)
    request.session.pop("password", None)
    return RedirectResponse("/", status_code=302)

# Función para verificar si un usuario existe
def user_exists(username):
    try:
        with open(USER_DB, "r", encoding='utf-8') as f:
            for line in f:
                saved_username, _ = line.strip().split(":")
                if saved_username == username:
                    return True
    except FileNotFoundError:
        return False
    return False

# Ruta POST para inscribirse en un sorteo
@app.post("/inscribirse")
async def inscribirse(request: Request):
    form_data = await request.form()
    nombre_sorteo = form_data.get("nombre_sorteo")
    user = get_current_user(request)

    if not user:
        return JSONResponse(status_code=401, content={"error": "Debes iniciar sesión para inscribirte en un sorteo."})

    # Leer los sorteos
    sorteos = leer_sorteos()

    # Buscar el sorteo en el que se quiere inscribir
    for sorteo in sorteos:
        if sorteo["nombre"] == nombre_sorteo:
            if user not in sorteo["participantes"]:
                sorteo["participantes"].append(user)
                escribir_sorteos(sorteos)  # Guardar los cambios
                return JSONResponse(status_code=200, content={"message": f"Te has inscrito en el sorteo {nombre_sorteo}"})
            else:
                return JSONResponse(status_code=400, content={"error": "Ya estás inscrito en este sorteo"})

    return JSONResponse(status_code=404, content={"error": "Sorteo no encontrado"})


# Función para autenticar a un usuario
def authenticate_user(username, password):
    try:
        with open(USER_DB, "r", encoding='utf-8') as f:
            for line in f:
                saved_username, saved_password = line.strip().split(":")
                if saved_username == username and saved_password == password:
                    return True
    except FileNotFoundError:
        return False
    return False
    
if __name__ == "__main__":
    try:
        port = int(os.environ.get("PORT", 8000))  # Usar puerto proporcionado por Railway
        uvicorn.run(app, host="0.0.0.0", port=port)
    except Exception as e:
        print(f"Error al iniciar la aplicación: {str(e)}")
