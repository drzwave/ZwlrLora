// @ts-check

// Z-Wave Geographic Location Command Class range test sample code
// This javascript runs under Z-Wave JS and Node.js which will poll a DUT
// every X seconds for it's GeoLoc coordinates and write them to a file which 
// then be imported into Excel which can then create Heat Maps.
// This version also pings up to 3 other DUTs that are traveling with the GeoLoc DUT.
//

const { Driver, CommandClass } = require("zwave-js");
const { CommandClasses, RFRegion, InterviewStage, RssiError } = require("@zwave-js/core");

const path = require("node:path");
const { setTimeout } = require("node:timers/promises");

const fs = require("node:fs/promises"); // data file to send coordinates to

process.on("unhandledRejection", (r) => {
  debugger;
  throw r;
});

/////////////////// REQUIRED CUSTOMIZATION ///////////////////////////////////
// UPDATE THE PORT name to the one currently connected
// or simply pass it as an argument to the script
const port = process.argv[2] ?? "COM5";
// Then update the keys as needed - extract them from Z-Wave JS UI.

const SecondsPerSample = 10; // UPDATE this with the desired time (in seconds) between samples - (1-100)

const FileName = `geoloc.csv`

// Replace the securityKeys below if desired...
// Or use these in the PCC and check the Override button in the Security menu
/////////////////////////////////////////////////////////////////////////////

const driver = new Driver(port, {
    logConfig: {        // uncomment these 4 lines if there are problems with the serialAPI
   	logToFile: true,    // they will create a log file in the current folder
  	forceConsole: true,
   },
  securityKeys: {
    S0_Legacy: Buffer.from("00000000000000000000000000000001", "hex"),
    S2_Unauthenticated: Buffer.from(
      "00000000000000000000000000000002",
      "hex",
    ),
    S2_Authenticated: Buffer.from(
      "0102030405060708090A0B0C0D0E0F03",
      "hex",
    ),
    S2_AccessControl: Buffer.from(
      "AACCAACCAACCAACCAACCAACCAACCAA04",
      "hex",
    ),
  },
  securityKeysLongRange: {
    S2_Authenticated: Buffer.from(
      "010203040506070809CAFEBABEBEEF05",
      "hex",
    ),
    S2_AccessControl: Buffer.from(
      "CCAACCAACCAACCAACCAACCAACCAACC06",
      "hex",
    ),
  },
  rf: {
    // Set the RF region to EU_LR on startup
    // region: RFRegion["Europe (Long Range)"],
    region: RFRegion["USA (Long Range)"],
    // Configure TX Power and LR Powerlevel if desired - 0 for US, 13 for EU
    txPower: {
      powerlevel: 0,
      measured0dBm: 0,
    },
    maxLongRangePowerlevel: 20,
  },
  storage: {
    cacheDir: path.join(__dirname, "cache"),
    lockDir: path.join(__dirname, "cache/locks"),
  },
  allowBootloaderOnly: true,
})
  .on("error", console.error)
  // When re-using the Z-Wave JS UI cache, comment out the line below (interviewNodes)
  // and uncomment the line after it (main)
  .once("driver ready", interviewNodes);
  // .once("driver ready", main);
void driver.start();

async function interviewNodes() {
  for (const node of driver.controller.nodes.values()) {
    // Force a new interview for all nodes that have been interviewed before
    if (node.isControllerNode) continue;
    if (node.interviewStage !== InterviewStage.Complete) {
      continue;
    }

    console.log(`Interviewing node ${node.id}...`);
    node.refreshInfo({
      resetSecurityClasses: true,
      waitForWakeup: true,
    });
  }

  driver.on("all nodes ready", main);
}

function nodeIdToFileName(nodeId) {
  return `geoloc_${nodeId.toString().padStart(3, "0")}.csv`;
}

async function main() {
  // Find the first node that supports Geolocation CC
  const geolocNode = [...driver.controller.nodes.values()]
    .find(node => node.supportsCC(CommandClasses["Geographic Location"]));
  if (!geolocNode) {
    console.error("No node supporting Geographic Location CC found");
    process.exit(1);
  }

  // Find all other nodes
  const otherNodes = [...driver.controller.nodes.values()]
  // except the controller itself
    .filter((node) => !node.isControllerNode)
    // and except the node that supports the Geolocation CC
    .filter((node) => node.id !== geolocNode.id)
    // and keep only those that support Firmware Update Meta Data CC
    .filter((node) => node.supportsCC(CommandClasses["Firmware Update Meta Data"]))

  const skippedNodes = [...driver.controller.nodes.values()]
    .filter((node) => node.isControllerNode || node.id === geolocNode.id)
    .filter((node) => !node.supportsCC(CommandClasses["Firmware Update Meta Data"]));

  await setTimeout(1000);
  
  // Print some info about the nodes
  console.log();
  console.log("All nodes interviewed")
  console.log(`Geoloc node: ${geolocNode.id}`);
  console.log(`Other nodes: ${otherNodes.map((node) => node.id).join(", ")}`);
  console.log(`Skipped nodes: ${skippedNodes.map((node) => node.id).join(", ")}`);
  console.log();

  await setTimeout(5000);

  let defaultMeshTxPower;
  try {
    defaultMeshTxPower = (await driver.controller.getPowerlevel()).powerlevel;
  } catch {
    defaultMeshTxPower = 0
  }
  
  const start = new Date();

  // Create a CSV file for each end device
//  for (const node of [geolocNode, ...otherNodes]) {
    await fs.appendFile(
      FileName,
//      nodeIdToFileName(node.id),
      `Time, Latitude, Longitude, Altitude, TxPower, RSSI, NodeID, Distance, ${start}\n`,
    );
//  }

  let txPower = 0;
  let ackRSSI = 0;
  let StartLat = 0;
  let StartLong= 0;
  let Distance = 0;
  let FirstLat = 0;
  let FirstLon = 0;
  
  while (true) {

    // Try to get the geographic location from the Geoloc node
    const geolocGet = new CommandClass({
      nodeId: geolocNode.id,
      ccId: CommandClasses["Geographic Location"],
      ccCommand: 0x02, // Get
    });

    // Set up a listener for the response, returning null if it times out
    const geolocResponse = driver
      .waitForCommand(
        (cc) =>
          cc.ccId === CommandClasses["Geographic Location"]
          && cc.ccCommand === 0x03,
        5000,
      )
      .catch(() => null);

    try { // ignore errors on a NACK
      // Send the command
      await driver.sendCommand(geolocGet, {
        // Extract the TX Power and RSSI from the TX Report when it is received
        onTXReport: (report) => {
          // The values behind ?? are used in case the info is not present in the report
          txPower = report.txPower ?? defaultMeshTxPower;
          ackRSSI = report.ackRSSI ?? RssiError.NotAvailable;
        },
      });
    } catch (error) {
      console.error(`Node ${geolocNode.id}: NACK`);
      await setTimeout(SecondsPerSample * 1000 / 4); // wait
      continue;
    }

    const payload = /** @type {CommandClass} */ (await geolocResponse)?.payload;
    if (!payload) {
      console.error(`Node ${geolocNode.id}: no response`);
      await setTimeout(SecondsPerSample * 1000 / 4); // wait
      continue;
    }

    // convert payload into .csv file coordinates
    const lon = payload.readInt32BE(0) / (1 << 23); // convert the fixed point value to floating point - the decimal point is bit 23
    const lat = payload.readInt32BE(4) / (1 << 23);
    const alt = payload.readIntBE(8, 3) / 100; // reading is in centimeters but most tools want meters
    const now = new Date();
    const time = now.toLocaleTimeString("en-US", {
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
    });
    const stat = payload[11];
    if (0==FirstLat) {  // compute the distance between the first point and the current point in meters
        FirstLat = lat;
        FirstLon = lon;
    } else {
        const X = lat-FirstLat;
        const Y = lon-FirstLon;
        Distance = Math.sqrt(X*X + Y*Y)*111.2*1000; // 111.2km per degree assuming short distances where curvature of earth doesn't matter
    }
    console.log("Lat=", lat, "Lon=", lon, "alt=", alt, "Sats=", stat>>4, "Distance=", Distance);

    if ((stat>>4) < 4) { // 4 or more satellites are required for a valid GPS reading
      console.log(`Invalid GPS reading`);
      await setTimeout(SecondsPerSample * 1000 / 4); // wait
      continue;
    }

    // We got a GPS reading, write the info to the CSV file for this node
    await fs.appendFile(
      FileName,
//      nodeIdToFileName(geolocNode.id),
      `${time}, ${lat}, ${lon}, ${alt}, ${txPower}, ${ackRSSI}, ${geolocNode.id}, ${Distance}\n`,
    );

    await setTimeout(SecondsPerSample * 1000 / 4); // wait

    // Now poll the rest of the nodes
    for (const node of otherNodes) {
      // Send a firmware update meta data get command to the node
      const response = await node.commandClasses["Firmware Update Meta Data"]
        .withTXReport()
        .getMetaData()
        .catch(() => null);

      if (response) {
        if (response.result) {
          // We got an ACK and a response
          const {txPower = defaultMeshTxPower, ackRSSI = RssiError.NotAvailable} = response.txReport ?? {};

          // Determine the current time again
          const now = new Date();
          const time = now.toLocaleTimeString("en-US", {
            hour: "2-digit",
            minute: "2-digit",
            second: "2-digit",
          });
          
          // And write the info to the CSV file for this node
          await fs.appendFile(
            FileName,
//            nodeIdToFileName(node.id),
            `${time}, ${lat}, ${lon}, ${alt}, ${txPower}, ${ackRSSI}, ${node.id}\n`,
          );
      
        } else {
          console.error(`Node ${node.id}: no response`);
        }
      } else {
        console.error(`Node ${node.id}: NACK`);
      }

      // After each node, wait a bit for the network to settle

      await setTimeout(SecondsPerSample * 1000 / 4); // wait
  /*
      // send an indicator to blink three times for a visual indicator that the DUT is still in range
      try {
        await node.commandClasses.Indicator.set([
          {
            indicatorId: 0x50,
            propertyId: 0x03,
            value: 2,
          },
          {
            indicatorId: 0x50,
            propertyId: 0x04,
            value: 3,
          },
        ]);
      } catch (error) {
        console.log("NACK");
      }

      // Wait before sending the next command
      await setTimeout(SecondsPerSample * 1000 / 2);
  */

    }
  }
}

// Destroy the driver instance when the application gets a SIGINT or SIGTERM signal
for (const signal of ["SIGINT", "SIGTERM"]) {
  process.on(signal, async () => {
    await driver.destroy();
    process.exit(0);
  });
}
