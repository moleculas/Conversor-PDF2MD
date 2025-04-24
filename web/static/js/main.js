// Funcionalidad para mostrar el nombre del archivo seleccionado
function setupFileUpload() {
    const fileInput = document.getElementById('pdf-file');
    if (!fileInput) return;
    
    fileInput.addEventListener('change', function(e) {
      const fileName = document.getElementById('selected-file');
      const fileNameContainer = document.getElementById('file-name');
      
      if (this.files && this.files.length > 0) {
        fileName.textContent = this.files[0].name;
        fileNameContainer.classList.remove('hidden');
      } else {
        fileNameContainer.classList.add('hidden');
      }
    });
  }
  
  // Inicializar todas las funcionalidades cuando el DOM está cargado
  document.addEventListener('DOMContentLoaded', () => {
    setupFileUpload();
  });