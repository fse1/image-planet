
// wait until the base HTML is loaded
document.addEventListener('DOMContentLoaded', function () {
    
    // get needed elements
    const mainContainer = document.querySelector('div.section-main-gallery');
    
    // create socket
    let socket = io();

    // join general notification room
    socket.emit('join-general-room');

    // handle new images. append to bottom of uploaded images
    socket.on('new-image-full', function (data) { 
   
      // handle the no image case
      const noImage = document.querySelectorAll('.section-main-gallery p.no-images');
      if (noImage.length > 0) {
        noImage[0].outerHTML = data.thumbnailhtml;
      }
      else
      {
        let newImageContainer = document.createElement("a");
        mainContainer.appendChild(newImageContainer);
        newImageContainer.outerHTML = data.thumbnailhtml;
      }

    });
    
});
