import "../modules/WebSDK/index";
import {
  FingerprintReader,
  SampleFormat,
  SamplesAcquired,
} from "@digitalpersona/devices";
import {
  Base64,
  BioSample,
  Utf8,
  Base64UrlString,
  Utf8String,
  Base64String,
} from "@digitalpersona/core";

function handleError(err: Error) {
  throw new Error(err?.message);
}

class FingerprintEnrollmentControl {
  private reader?: FingerprintReader;
  public finger?: string;
  public leftImage?: string;
  public rightImage?: string;
  public user?: string;
  public acquisitionStarted?: boolean = false;

  constructor(user: string) {
    this.init(user);
    this.leftImage = "";
    this.rightImage = "";
  }

  async init(user: string) {
    this.reader = new FingerprintReader();
    this.user = user;
    this.reader.on("DeviceConnected", this.onDeviceConnected);
    this.reader.on("DeviceDisconnected", this.onDeviceDisconnected);
    this.reader.on("QualityReported", this.onQualityReported);
    this.reader.on("SamplesAcquired", this.onSamplesAcquired);
    this.reader.on("ErrorOccurred", this.onReaderError);
    this.reader.on("AcquisitionStopped", this.onAcquisitionStopped);
    this.reader.on("AcquisitionStarted", this.onAcquisitionStarted);
  }

  // Event handlers.
  private onDeviceConnected = (event: any) => {
    console.log("connected", event);
  };
  private onAcquisitionStopped = (event: any) => {
    console.log("connection stopped", event);
    this.acquisitionStarted = false;
  };
  private onAcquisitionStarted = (event: any) => {
    this.acquisitionStarted = true;
  };
  private onDeviceDisconnected = (event: any) => {
    console.log("disconnected");
  };
  private onQualityReported = (event: any) => {
    console.log("object");
  };
  private onSamplesAcquired = (data: SamplesAcquired) => {
    try {
      const samples: BioSample[] = data?.samples;
      if (!samples) return;
      const encodedSampleData: any = samples[0];
      const base64ImageData: Base64String =
        Base64.fromBase64Url(encodedSampleData);
      const imageUrl = `data:image/png;base64, ${base64ImageData}`;

      if (this.finger == "index_left_finger") {
        this.leftImage = imageUrl;
        $("#index_left_finger").html(
          '<span class="icon icon-indexfinger-not-enrolled" title="not_enrolled"></span>'
        );
        $("#leftImage").attr("src", imageUrl);
      } else {
        this.rightImage = imageUrl;
        $("#index_right_finger").html(
          '<span class="icon icon-indexfinger-not-enrolled" title="not_enrolled"></span>'
        );
        $("#rightImage").attr("src", imageUrl);
      }
      console.log(imageUrl);
    } catch (error) {
      handleError(error);
    }
  };

  private onReaderError = (event: any) => {
    console.log(event, "error");
  };

  public async captureFingerprint() {
    try {
      await this.reader.startAcquisition(SampleFormat.PngImage);
    } catch (err) {
      handleError(err);
      console.log(err);
    }
  }

  public async displayReader() {
    let readers = await this.reader.enumerateDevices(); // grab available readers here
    console.log(readers);
    // when promise is fulfilled
    if (readers.length > 0) {
    } else {
      alert("please connect fingerprint reader");
    }
  }

  public destroy() {
    if (this.reader) {
      this.reader.stopAcquisition();
      this.reader.off();
      delete this.reader;
    }
  }
}

class FingerprintVerify {
  private reader?: FingerprintReader;
  public fingerPrint?: string = "";
  public acquisitionStarted?: boolean = false;

  constructor() {
    this.reader = new FingerprintReader();
    this.reader.on("DeviceConnected", this.onDeviceConnected);
    this.reader.on("DeviceDisconnected", this.onDeviceDisconnected);
    this.reader.on("QualityReported", this.onQualityReported);
    this.reader.on("SamplesAcquired", this.onSamplesAcquired);
    this.reader.on("ErrorOccurred", this.onReaderError);
    this.reader.on("AcquisitionStopped", this.onAcquisitionStopped);
    this.reader.on("AcquisitionStarted", this.onAcquisitionStarted);
  }

  // Event handlers.
  private onDeviceConnected = (event: any) => {
    console.log("connected", event);
  };
  private onAcquisitionStopped = (event: any) => {
    console.log("connection stopped", event);
    this.acquisitionStarted = false;
  };
  private onAcquisitionStarted = (event: any) => {
    this.acquisitionStarted = true;
  };
  private onDeviceDisconnected = (event: any) => {
    console.log("disconnected");
  };
  private onQualityReported = (event: any) => {
    console.log("object");
  };
  private onSamplesAcquired = (data: SamplesAcquired) => {
    $("#verifyloader").removeClass("visually-hidden");
    try {
      const samples: BioSample[] = data?.samples;
      if (!samples) return;
      const encodedSampleData: any = samples[0];
      const base64ImageData: Base64String =
        Base64.fromBase64Url(encodedSampleData);
      const imageUrl = `data:image/png;base64, ${base64ImageData}`;

      this.fingerPrint = imageUrl;
      const formData = new FormData();
      if (this.fingerPrint != "") {
        formData.append("fingerprint", this.fingerPrint);
        // AJAX post request to backend
        $.ajax({
          url: "/verify",
          data: formData,
          type: "POST",
          processData: false,
          contentType: false,
          success: function (data) {
            $("#verifyloader").addClass("visually-hidden");
            if (data.success) {
              alert(`Access Granted, Welcome ${data.user.name}`);
              $("#fingerprintModal").modal("hide");
              $("#doorOpen1").addClass("doorOpen1");
              $("#doorOpen2").addClass("doorOpen2");
            } else {
              alert(`Access Denied, User not found \nPlease clean or try a different finger `);
            }
          },
          error: function (err) {
            console.log(err);
            alert("Error");
          },
        });
      } else {
        alert("Please place index finger on scanner");
      }
    } catch (error) {
      handleError(error);
    }
  };

  private onReaderError = (event: any) => {
    console.log(event, "error");
  };

  public async captureFingerprint() {
    try {
      await this.reader.startAcquisition(SampleFormat.PngImage);
    } catch (err) {
      handleError(err);
    }
  }

  public destroy() {
    if (this.reader) {
      this.reader.stopAcquisition();
      this.reader.off();
      delete this.reader;
    }
  }
}

// collect user id of fingerprints to be enrolled
const user_id = $("#user_id").val();

// create an instance of the enrollment class
let myReader = new FingerprintEnrollmentControl(user_id?.toString());

// capture user right index
$("#captureRightButton").on("click", function () {
  myReader.finger = "index_right_finger";

  $("#index_right_finger").html(
    `<span class="icon capture-indexfinger" title="not_enrolled"></span>`
  );

  if (myReader.finger != null) {
    myReader.captureFingerprint();
  }
});

// capture user left index
$("#captureLeftButton").on("click", function () {
  myReader.finger = "index_left_finger";

  $("#index_left_finger").html(
    `<span class="icon capture-indexfinger" title="not_enrolled"></span>`
  );

  if (myReader.finger != null) {
    myReader.captureFingerprint();
  }
});

$("#clearButton").on("click", function () {
  $("#leftImage").attr("src", "/static/finger.jpeg");
  $("#rightImage").attr("src", "/static/finger.jpeg");
  myReader.rightImage = "";
  myReader.leftImage = "";
  myReader.finger = "";
});

// send fingerprints to flask backend for enrollment
$("#submitButton").on("click", function () {
  const formData = new FormData();
  if (myReader.leftImage != "" && myReader.rightImage != "") {
    formData.append("left_finger", myReader.leftImage);
    formData.append("right_finger", myReader.rightImage);
    formData.append("user_id", myReader.user);
    // AJAX post request to backend
    $.ajax({
      url: "/fingerprint",
      data: formData,
      type: "POST",
      processData: false,
      contentType: false,
      success: function (data) {
        alert("Enrollment Successful");
        myReader.destroy();
        window.location.href = "/";
      },
      error: function (err) {
        alert("Error");
      },
    });
  } else {
    alert("Please enroll both fingers");
  }
});

$("#fingerprintModal").on("show.bs.modal", async function (e) {
  const verify = new FingerprintVerify();
  $("#doorOpen1").removeClass("doorOpen1");
  $("#doorOpen2").removeClass("doorOpen2");
  await verify.captureFingerprint();
});

// $("#fingerprintModal").on("hidden.bs.modal", async function (e) {
//   verify.destroy();
// });
