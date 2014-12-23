var waiting_for_update = false, 
    LONG_POLL_DURATION = 22000,
    last_board_num = 0,
    boards = {}; 
    


function wait_for_update() {

    if (!waiting_for_update) {
        waiting_for_update = true;
        $.ajax({ url: '/poll/'+last_board_num,
                 success: function(data){
                            display_data(data), 
                            setTimeout(wait_for_update);
                 },
                 complete: function () {
                    waiting_for_update = false;
                    setTimeout(wait_for_update, 3000); 
                 },
                 timeout:  LONG_POLL_DURATION,
                 error: function () {
                     setTimeout(wait_for_update, 3000);
                 },
               });
    }
}

function display_data(data_list) {
    var i;
    
    for (i=0; i<data_list.length; i++){
        data = data_list[i];
        console.log(data);
        boards[data.board_num] = data;
        last_board_num = data.board_num;
        
        $('div#contents').append(data.content);
        
        $("#updated").fadeIn('fast');
        setTimeout(function() {  $("#updated").fadeOut('slow');  }, 2500);
    }
}

