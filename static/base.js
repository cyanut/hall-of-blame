var waiting_for_update = false, 
    LONG_POLL_DURATION = 10000,
    last_board_num = 0,
    boards = []; 
    


function wait_for_update() {

    if (!waiting_for_update) {
        waiting_for_update = true;
        $.ajax({ url: '/test/'+last_board_num,
                 success: function(msg){
                            display_data(msg), 
                            setTimeout(wait_for_update, 5000);
                 },
                 complete: function () {
                    waiting_for_update = false;
                    setTimeout(wait_for_update, 5000); 
                 },
                 timeout:  LONG_POLL_DURATION,
                 error: function () {
                     setTimeout(wait_for_update, 30000);
                 },
               });
    }
}

function display_data(data_list_raw) {
    var i;
    var data_list = JSON.parse(data_list_raw);
    var data;
    for (i=0; i<data_list.length; i++){
        data = data_list[i];
        if ($.inArray(data.board_num, boards) === -1){
            console.log("new");
            boards.push(data.board_num);
            if (last_board_num < data.board_num){
                last_board_num = data.board_num;
            }
            $('div#contents').append(data.content);
        } else {
            objs = $(data.content);
            console.log("replace", objs.length);
            for (var i=0; i<objs.length; i++){
                if (objs[i].nodeType != 1) continue;
                
                if (objs[i].tagName.toLowerCase() == 'script'){
                    //run additional scripts
                    eval(obj[i].text);
                } else {
                    //update elements
                    target = $('#'+objs[i].id);
                    if (target.length > 0){
                        target = target[0];
                        target.outerHTML = objs[i].outerHTML;
                    }
                }
            }
        }
        
        $("#updated").fadeIn('fast');
        setTimeout(function() {  $("#updated").fadeOut('slow');  }, 2500);
    }
}

