
var mcloudApp = angular.module('mcloudApp', []);


mcloudApp.controller('McloudAppsCtrl', function ($scope, $interval) {
    var io = new McloudIO(location.hostname, location.port);

    $scope.selection = {
        app: 'new',
        service: null,
        service_tab: null
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

        if ($scope.selection.service && $scope.selection.service.log_terminal) {
            $scope.selection.service.log_terminal.destroy();
        }

        if ($scope.selection.service && $scope.selection.service.run_terminal) {
            $scope.selection.service.run_terminal.destroy();
        }

        $scope.selection.service = service;

        if ($scope.selection.service_tab == 'inspect' || ! $scope.selection.service_tab) {
            $scope.service_inspect(service);
        }

        if ($scope.selection.service_tab == 'logs') {
            $scope.service_logs(service);
        }
    };

    $scope.service_inspect = function(service) {
        $scope.selection.service_tab = 'inspect';

        io.inspect($scope.selection.app.name, $scope.selection.service.shortname).then(function(result) {
            service.inspect = result;
            $scope.$apply();
        });
    };

    $scope.service_logs = function(service) {
        $scope.selection.service_tab = 'logs';

        if (!service.log_terminal) {
            service.log_terminal = new Terminal({
              cols: 80,
              rows: 24,
              screenKeys: false
            });
        }

        io.logs(service.name).then(function(task) {
            service.log_terminal.reset();
            $scope.service_tasks.push(task.id);

            task.on('progress', function(data) {
                if (service.log_terminal) {
                    service.log_terminal.writeln(data);
                }
            });

            $scope.$apply();
        });
    };

    $scope.service_run = function(service) {
        $scope.selection.service_tab = 'run';

        if (!service.run_terminal) {
            service.run_terminal = new Terminal({
              cols: 80,
              rows: 24,
              screenKeys: true
            });
        }

        io.run(service.name, 'bash', 80, 40).then(function(task) {
            service.run_terminal.reset();

            $scope.service_tasks.push(task.id);

            task.on('stdout', function(data) {
                service.run_terminal.write(atob(data));
            });

            service.run_terminal.on('data', function(data) {
               task.stdin(btoa(data));
            });

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

mcloudApp.directive('xterm', function() {
    console.log('Registred');

  function link(scope, element, attrs) {
      var term = null;
      console.log('Directive works!');

      scope.$watch(attrs.term, function (value){
          term = value;

          console.log(term);

          if (term) {
              term.open(element[0]);
          }

      });
  }

  return {
      restrict: 'E',
      link: link
  };
});