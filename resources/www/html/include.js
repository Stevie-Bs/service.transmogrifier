var base_url = '/api.json'
var __queue_poll__ = false;
var __id__ = false;
var __file__ = ''
var __files__ = []
function notify(text) {
	$("#notes").html(text);
}
var format_size = function(fileSizeInBytes) {
	var i = -1;
	var byteUnits = [' kB', ' MB', ' GB', ' TB', 'PB', 'EB', 'ZB', 'YB'];
	do {
		fileSizeInBytes = fileSizeInBytes / 1024;
		i++;
	} while (fileSizeInBytes > 1024);
	return Math.max(fileSizeInBytes, 0.1).toFixed(1) + byteUnits[i];
};
if (!String.prototype.format) {
	String.prototype.format = function() {
		var args = arguments;
		return this.replace(/{(\d+)}/g, function(match, number) { 
			return typeof args[number] != 'undefined'
			? args[number]
			: match
			;
		});
	};
}
function setCookie(cname, cvalue, exdays) {
	var d = new Date();
	d.setTime(d.getTime() + (exdays*24*60*60*1000));
	var expires = "expires="+d.toUTCString();
	document.cookie = cname + "=" + cvalue + "; " + expires;
}
function getCookie(cname) {
	var name = cname + "=";
	var ca = document.cookie.split(';');
	for(var i=0; i<ca.length; i++) {
		var c = ca[i];
		while (c.charAt(0)==' ') c = c.substring(1);
		if (c.indexOf(name) == 0) return c.substring(name.length,c.length);
	}
	return "";
}
function refreshPage(href) {
	$.mobile.changePage(
			href,{
			allowSamePageTransition	: true,
			transition				: 'none',
			showLoadMsg				: false,
			reloadPage				: true
			}
	);
}
function validateToken(token) {
	data = JSON.stringify({"method": "validate_token", "token": token})
	status = false;
	$.post(base_url, data, function(json) {
		status = json['status'];
		return status;
	});
}
var token = getCookie('token')