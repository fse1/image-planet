
// wait until the base HTML is loaded
document.addEventListener('DOMContentLoaded', function () {
    
    // create socket
    let socket = io();

    // handle new messages. change the style of the header
    socket.on('new-dm', newNotificationDM);
    
});
