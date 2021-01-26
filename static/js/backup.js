
$(document).ready(function() {

  $('#myModal').dialog({
                autoOpen: false,
                title: 'Basic Dialog'
            });

    //hang on event of form with id=myform
    $('#backupButton').click(function(event) {

    event.preventDefault();
    var actionurl = window.location.href + '/backup';

    //do your own request an handle the results
    $.ajax({
        async: false,
        url: actionurl,
        type: 'post',
        dataType: 'application/json',
        data: $("#target").serialize(),
        success: function(data) {
            alert( "Handler for .submit() sucess." );
        }
    });

    location.reload();

   });
    $('#restoreButton').click(function(event) {

    event.preventDefault();

    var actionurl = window.location.href + '/restore';

    console.log(actionurl);

    var restoreModules = [];
    $('#restore-form input:checked').each(function() {
        restoreModules.push($(this).attr('name'));
    });
     console.log(restoreModules);

     console.log($("#restore-form").serialize());

    //do your own request an handle the results
    $.ajax({
        async: false,
        url: actionurl,
        type: 'post',
        dataType: 'application/json',
        data: $("#restore-form").serialize(),
        success: function(data) {
            alert( "Handler for .submit() sucess." );
        }
    });

   // location.reload();

   });
    $('#deleteButton').click(function(event) {

    event.preventDefault();

    var actionurl = window.location.href + '/delete';

    console.log(actionurl);

    //do your own request an handle the results
    $.ajax({
        async: false,
        url: actionurl,
        type: 'post',
        dataType: 'application/json',
        data: $("#restore-form").serialize(),
        success: function(data) {
            alert( "Handler for .submit() sucess." );
        }
    });

    location.reload();

   });
    $('#compareButton').click(function(event) {

    event.preventDefault();

    var actionurl = window.location.href + '/compare';

    var currentConfigCompare = [];
    $('#existingTable input:checked').each(function() {
        currentConfigCompare.push($(this).attr('name'));
    });

    var backedUpConfig = [];
    $('#backedupTable input:checked').each(function() {
        backedUpConfig.push($(this).attr('name'));
    });

    var dict = {};

    dict["currentConfigCompare"] = currentConfigCompare;
    dict["backedUpConfig"] = backedUpConfig;


    //do your own request an handle the results
    $.ajax({
        async: false,
        url: actionurl,
        type: 'POST',
        contentType: "application/json",
        data: JSON.stringify(dict),
        success: function(html,data) {
            console.log(html);
            $("#compareText").html(html);
            }
    });

    $("#myModal").dialog("open");

    // location.reload();

   });

$("body").on('click', ".close", function(){
    $("#myModal").dialog("close");

    });

});

