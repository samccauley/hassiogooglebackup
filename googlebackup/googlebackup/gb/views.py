import json
import logging
import traceback

from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt
from gbcommon import (
    adhocBackupFiles,
    backupFiles,
    fetchAndSaveTokens,
    getOptions,
    publishAdhocResult,
    publishConfiguredResult,
    purgeOldFiles,
    purgeOldGoogleFiles,
    requestAuthorization,
)


def index(request):
    return render(request, "gb/index.html")


def getAuth(request):

    authorization_url, state = requestAuthorization()

    # Save the value returned for state
    request.session["state"] = state
    logging.debug("State saved into session: " + state)

    return HttpResponseRedirect(authorization_url)


def authConfirmed(request):

    saved_state = request.session["state"]
    logging.debug("State retrieved from session: " + saved_state)
    authorizationCode = request.POST.get("authorizationCode")
    logging.debug("Authorization code submitted for ingestion: " + authorizationCode)

    fetchAndSaveTokens(
        saved_state,
        request.build_absolute_uri(reverse("gb:authConfirmed")),
        request.build_absolute_uri(),
        authorizationCode,
    )

    return render(request, "gb/authConfirmed.html")


@csrf_exempt
def adhocBackup(request):

    logging.debug("adhocBackup request.body: " + str(request.body))

    json_request = json.loads(request.body)
    fromPatterns = json_request["fromPatterns"]
    backupDirID = json_request["backupDirID"]

    adhocBackupResult = {}
    status = 200
    try:
        adhocBackupResult = adhocBackupFiles(
            fromPatterns, backupDirID, request.build_absolute_uri("/")
        )
    except Exception as e:
        logging.error(traceback.format_exc())
        adhocBackupResult = {"errorMessage": str(e)}
        status = 500

    logging.info("googlebackup adhocBackup result: " + str(adhocBackupResult))

    try:
        publishAdhocResult(adhocBackupResult)
    except Exception:
        logging.warning(traceback.format_exc())

    return JsonResponse(adhocBackupResult, status=status)


def doBackup(request):

    options = getOptions()
    fromPattern = options["fromPattern"]
    backupDirID = options["backupDirID"]
    doPurge = options["purge"]["enabled"]
    preserve = options["purge"]["preserve"]
    doGooglePurge = options["purge_google"]["enabled"]
    preserveInGoogle = options["purge_google"]["preserve"]

    backupResult = {}
    status = 200
    try:
        backupResult = backupFiles(
            fromPattern, backupDirID, request.build_absolute_uri("/")
        )
        if doPurge:
            deletedCount = purgeOldFiles(fromPattern, preserve)
            backupResult["deletedCount"] = deletedCount
        if doGooglePurge:
            deletedFromGoogleCount = purgeOldGoogleFiles(
                backupDirID, preserveInGoogle, request.build_absolute_uri("/")
            )
            backupResult["deletedFromGoogle"] = deletedFromGoogleCount
    except Exception as e:
        logging.error(traceback.format_exc())
        backupResult = {"errorMessage": str(e)}
        status = 500

    logging.info("googlebackup result: " + str(backupResult))

    try:
        publishConfiguredResult(backupResult)
    except Exception:
        logging.warning(traceback.format_exc())

    return JsonResponse(backupResult, status=status)
