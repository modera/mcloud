
var mcloudApp = angular.module('mcloudApp', []);



mcloudApp.controller('McloudAppsCtrl', function ($scope, $interval) {
    var io = new McloudIO(location.hostname);

    $scope.selection = {
        app: 'new',
        service: null
    };

    $scope.select_app = function(app) {
        $scope.selection.app = app;
        $scope.selection.service = null;
    };

    $scope.select_service = function(service) {
        $scope.selection.service = service;

        io.inspect($scope.selection.app.name, $scope.selection.service.shortname).then(function(result) {
            service.inspect = result;
            $scope.$apply();
        });
    };

    $scope.update_apps = function() {
        io.list().then(function(result) {
            $scope.apps = result;

            if ($scope.selection.app) {
                angular.forEach($scope.apps, function(app) {
                    if (app.name == $scope.selection.app.name) {
                        $scope.selection.app = app;
                    }
                });
            }

            $scope.$apply();
        });
    };

    $scope.update_apps();

});