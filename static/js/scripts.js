document.addEventListener("DOMContentLoaded", function () {
  const registerForm = document.getElementById("registerForm");
  const assignButton = document.getElementById("assignButton");
  const resultDiv = document.getElementById("result");

  // Registro de usuarios
  registerForm.addEventListener("submit", function (event) {
    event.preventDefault();
    const name = document.getElementById("name").value;

    fetch("/register", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ name: name }),
    })
      .then((response) => {
        if (!response.ok) {
          return response.json().then((data) => {
            throw new Error(data.detail);
          });
        }
        return response.json();
      })
      .then((data) => {
        alert(data.message);
        window.location.reload();
      })
      .catch((error) => {
        alert("Error: " + error.message); // Mostrar el error de validación
      });
  });

  // Asignar amigos invisibles
  assignButton.addEventListener("click", function () {
    fetch("/assign", {
      method: "POST",
    })
      .then((response) => response.json())
      .then((data) => {
        alert(data.message);
        window.location.reload();
      })
      .catch((error) => console.error("Error:", error));
  });
});

// Manejar el botón "Ver quien te ha tocado"
document.querySelectorAll(".ver-asignacion-btn").forEach(function (button) {
  button.addEventListener("click", async function (event) {
    event.preventDefault(); // Evitar el comportamiento por defecto del botón

    const nombreSorteo = button.getAttribute("data-nombre-sorteo");
    const participante = button.getAttribute("data-participante");

    try {
      const response = await fetch(
        `/ver-asignacion/${nombreSorteo}/${participante}`,
        {
          method: "GET",
        }
      );

      if (response.ok) {
        const result = await response.json(); // Obtener el JSON solo si la respuesta es ok
        alert(result.message); // Mostrar el mensaje del servidor
      } else {
        const errorResult = await response.json(); // Obtener el error en formato JSON
        alert(errorResult.error); // Mostrar el mensaje de error
      }
    } catch (error) {
      alert("Ocurrió un error al intentar obtener la asignación."); // Mensaje de error genérico
    }
  });
});

// Manejar el botón "Volver a empezar el sorteo"
document.querySelectorAll(".reiniciar-sorteo-btn").forEach(function (button) {
  button.addEventListener("click", async function (event) {
    event.preventDefault(); // Evitar comportamiento por defecto

    const nombreSorteo = button.getAttribute("data-nombre-sorteo");

    // Solicitar al servidor que reinicie el sorteo
    const response = await fetch(`/reiniciar-sorteo/${nombreSorteo}`, {
      method: "POST",
    });

    if (response.ok) {
      const result = await response.json();
      alert(result.message); // Mostrar mensaje de éxito
      window.location.reload(); // Recargar la página para ver los cambios
    } else {
      const errorResult = await response.json();
      alert(errorResult.error); // Mostrar mensaje de error
    }
  });
});
