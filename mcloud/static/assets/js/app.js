
var mcloudApp = angular.module('mcloudApp', []);



mcloudApp.controller('McloudAppsCtrl', function ($scope, $interval) {
    var io = new McloudIO(location.hostname);

    $scope.selection = {
        app: 'new',
        service: null
    };

    $scope.service_tasks = [];

    $scope.kill_service_tasks = function() {
        angular.forEach($scope.service_tasks, function(task_id) {
            console.log('kill', task_id);
            io.kill(task_id)
        });
        $scope.service_tasks = [];
    };

    $scope.select_app = function(app) {
        $scope.kill_service_tasks();

        $scope.selection.app = app;
        $scope.selection.service = null;
    };

    $scope.select_service = function(service) {
        $scope.kill_service_tasks();

        $scope.selection.service = service;

        io.inspect($scope.selection.app.name, $scope.selection.service.shortname).then(function(result) {
            service.inspect = result;
            $scope.$apply();
        });

        $scope.service_logs(service);
    };

    $scope.service_logs = function(service) {
        io.logs(service.name).then(function(task) {

            $scope.service_tasks.push(task.id);

            task.on('progress', function(data) {
//                console.log(data);
            })
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