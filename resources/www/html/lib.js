$(document).ready(function() {
});

function notify(text) {
	
}


$(document).delegate('#tvshows', 'pageshow', function () {

});


$(document).delegate('#movies', 'pageshow', function () {


});

$(document).delegate('#queue', 'pageshow', function () {
	$.getJSON('/query/?method=getQueue', function(json) {
		html = ''
		$.each(json, function(index){
			row = json[index]
			html += '<li class="queueListItem" value="'+row[0]+'">'+row[1]+' - '+row[2]+'</li>'		
		});
		$('#queueList').html(html);
		$('#queueList').listview("refresh");	
	});
});

$(document).delegate('#log', 'pageshow', function () {
	$.ajax({
		        type: "GET",
		        url: "/query/?method=getLogContent",
		        cache: false,
		        success: function(response) {
				
				$('#logcontent').html('<pre>' + response + '</pre>');
			}
		});


});
