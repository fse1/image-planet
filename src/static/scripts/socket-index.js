

// wait until the base HTML is loaded
document.addEventListener('DOMContentLoaded', function () {
    
    // get needed elements
    const recentContainer = document.querySelector('div.recent-image-container');
    
    // create socket
    let socket = io();
    console.log('here')
    socket.emit('join-general-room');
    console.log('after')
    socket.on('new-image-full', function (data) { 
      let newImageContainer = document.createElement("div")
      recentContainer.insertBefore(newImageContainer, recentContainer.childNodes[3])
      newImageContainer.outerHTML = data.html
      console.log(data.html)
    });
    
});
